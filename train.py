# === FILE: train.py ===
# GymSense AI — Training script for Hybrid CNN-Dilated Self-Attention model
# Target: Lightning AI, NVIDIA RTX 6000 (24 GB VRAM)

import os
import sys
import json
import argparse
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    accuracy_score, f1_score, cohen_kappa_score,
    classification_report, confusion_matrix
)
import joblib
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, regularizers, constraints, callbacks

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

# ──────────────────────────────────────────────
# GPU Configuration
# ──────────────────────────────────────────────

def configure_gpu():
    """Configure GPU memory growth and return list of available GPUs."""
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print(f"[GPU] Found {len(gpus)} GPU(s)")
        for g in gpus:
            print(f"  → {g.name}")
    else:
        print("[GPU] No GPU found — using CPU")
    return gpus

# ──────────────────────────────────────────────
# Data Loading & Preprocessing
# ──────────────────────────────────────────────

SENSOR_COLS = {
    'combine': ['A_x', 'A_y', 'A_z', 'G_x', 'G_y', 'G_z', 'C_1'],
    'imu':     ['A_x', 'A_y', 'A_z', 'G_x', 'G_y', 'G_z'],
    'cap':     ['C_1'],
}

CLASS_WEIGHTS = {
    0: 17.34, 1: 16.14, 2: 18.45, 3: 18.89, 4: 15.50,
    5: 1.0,   6: 9.79,  7: 46.91, 8: 12.4,  9: 10.2,
    10: 9.14, 11: 9.1,
}


def load_and_filter(data_path, position='wrist'):
    """Load RecGym.csv and filter to the specified sensor position."""
    print(f"[DATA] Loading {data_path} ...")
    df = pd.read_csv(data_path)
    print(f"[DATA] Raw shape: {df.shape}")

    df = df[df['Position'] == position].copy()
    df.dropna(inplace=True)
    print(f"[DATA] After filtering to '{position}': {df.shape}")
    return df


def create_windows(data, labels, window_size=80, stride=40):
    """Create overlapping windows from continuous sensor data."""
    X_windows, y_windows = [], []
    n_samples = len(data)

    for start in range(0, n_samples - window_size + 1, stride):
        end = start + window_size
        window = data[start:end]
        window_labels = labels[start:end]

        # Majority label for the window
        values, counts = np.unique(window_labels, return_counts=True)
        majority_label = values[np.argmax(counts)]

        X_windows.append(window)
        y_windows.append(majority_label)

    return np.array(X_windows), np.array(y_windows)


def prepare_data(df, sensor_mode, test_user, window_size=80, stride=40):
    """Full preprocessing: split, scale, window, encode labels."""
    cols = SENSOR_COLS[sensor_mode]
    n_channels = len(cols)

    # Label encoding
    le = LabelEncoder()
    le.fit(df['Workout'].unique())
    n_classes = len(le.classes_)
    print(f"[DATA] Classes ({n_classes}): {list(le.classes_)}")

    # LOUO split
    train_df = df[df['Subject'] != test_user].copy()
    test_df  = df[df['Subject'] == test_user].copy()
    print(f"[DATA] Train subjects: {sorted(train_df.Subject.unique())} ({len(train_df)} samples)")
    print(f"[DATA] Test  subject:  [{test_user}] ({len(test_df)} samples)")

    # Fit scaler on training data only
    scaler = StandardScaler()
    train_scaled = scaler.fit_transform(train_df[cols].values)
    test_scaled  = scaler.transform(test_df[cols].values)

    train_labels = le.transform(train_df['Workout'].values)
    test_labels  = le.transform(test_df['Workout'].values)

    # Create windows per subject-day to avoid cross-session contamination
    X_train_all, y_train_all = [], []
    for (subj, day), group in train_df.groupby(['Subject', 'Day']):
        idx = group.index
        mask = np.isin(train_df.index, idx)
        positions = np.where(mask)[0]
        if len(positions) < window_size:
            continue
        s_data = train_scaled[positions]
        s_labels = train_labels[positions]
        Xw, yw = create_windows(s_data, s_labels, window_size, stride)
        X_train_all.append(Xw)
        y_train_all.append(yw)

    X_test_all, y_test_all = [], []
    for (subj, day), group in test_df.groupby(['Subject', 'Day']):
        idx = group.index
        mask = np.isin(test_df.index, idx)
        positions = np.where(mask)[0]
        if len(positions) < window_size:
            continue
        s_data = test_scaled[positions]
        s_labels = test_labels[positions]
        Xw, yw = create_windows(s_data, s_labels, window_size, stride)
        X_test_all.append(Xw)
        y_test_all.append(yw)

    X_train = np.concatenate(X_train_all, axis=0)
    y_train = np.concatenate(y_train_all, axis=0)
    X_test  = np.concatenate(X_test_all, axis=0)
    y_test  = np.concatenate(y_test_all, axis=0)

    # Reshape to (batch, 1, window_size, n_channels)
    X_train = X_train.reshape(-1, 1, window_size, n_channels)
    X_test  = X_test.reshape(-1, 1, window_size, n_channels)

    # One-hot encode labels
    y_train_cat = keras.utils.to_categorical(y_train, n_classes)
    y_test_cat  = keras.utils.to_categorical(y_test, n_classes)

    # Sample weights for class imbalance
    sample_weights = np.array([CLASS_WEIGHTS.get(int(y), 1.0) for y in y_train])

    print(f"[DATA] X_train: {X_train.shape}, X_test: {X_test.shape}")
    print(f"[DATA] y_train: {y_train_cat.shape}, y_test: {y_test_cat.shape}")

    return (X_train, y_train_cat, X_test, y_test_cat,
            y_train, y_test, sample_weights,
            scaler, le, n_classes, n_channels)

# ──────────────────────────────────────────────
# Model Architecture: Hybrid CNN-Dilated Self-Attention
# ──────────────────────────────────────────────

def conv_block(input_tensor, in_chans, F1=32, D=4, kernel_size=20, name_prefix=''):
    """
    Conv_block_ as specified in the paper.
    Input: (batch, 80, in_chans, 1)  [after Permute]
    Output: (batch, 80, 1, F1*D)  — spatial dim preserved for concat
    """
    x = layers.Conv2D(
        F1, (kernel_size, 1), padding='same', use_bias=True,
        kernel_regularizer=regularizers.L2(0.009),
        kernel_constraint=constraints.max_norm(0.8),
        name=f'{name_prefix}_conv1'
    )(input_tensor)
    x = layers.LayerNormalization(name=f'{name_prefix}_ln1')(x)
    x = layers.Activation('elu', name=f'{name_prefix}_elu1')(x)

    x = layers.DepthwiseConv2D(
        (1, in_chans), depth_multiplier=D, use_bias=True,
        depthwise_regularizer=regularizers.L2(0.009),
        depthwise_constraint=constraints.max_norm(0.8),
        name=f'{name_prefix}_dwconv'
    )(x)
    x = layers.LayerNormalization(name=f'{name_prefix}_ln2')(x)
    x = layers.Activation('elu', name=f'{name_prefix}_elu2')(x)
    x = layers.Dropout(0.1, name=f'{name_prefix}_drop1')(x)

    F2 = F1 * D  # 128
    x = layers.Conv2D(
        F2, (10, 1), padding='same', use_bias=True,
        kernel_regularizer=regularizers.L2(0.009),
        kernel_constraint=constraints.max_norm(0.8),
        name=f'{name_prefix}_conv2'
    )(x)
    x = layers.LayerNormalization(name=f'{name_prefix}_ln3')(x)
    x = layers.Activation('elu', name=f'{name_prefix}_elu3')(x)
    x = layers.Dropout(0.1, name=f'{name_prefix}_drop2')(x)

    # Output shape: (batch, 80, 1, F2=128)
    return x


def mha_block(input_tensor, name_prefix=''):
    """
    Multi-Head Attention block with residual connection.
    Input/Output: (batch, T_w, F)
    """
    x = layers.LayerNormalization(epsilon=1e-6, name=f'{name_prefix}_mha_ln')(input_tensor)
    x = layers.MultiHeadAttention(
        num_heads=4, key_dim=8, dropout=0.1,
        name=f'{name_prefix}_mha'
    )(x, x)
    x = layers.Dropout(0.3, name=f'{name_prefix}_mha_drop')(x)
    x = layers.Add(name=f'{name_prefix}_mha_add')([input_tensor, x])
    return x


def di_block(input_tensor, window_idx, name_prefix=''):
    """
    Dilated TCN block with 2 stages.
    Stage 1: dilation=1
    Stage 2: dilation=2^(window_idx+1)
    Input: (batch, T_w, F)
    Output: (batch, T_w, 32)
    """
    def dilated_stage(x, dilation_rate, stage_name):
        residual = x
        x = layers.Conv1D(
            32, 3, dilation_rate=dilation_rate, padding='causal',
            activation='linear',
            kernel_regularizer=regularizers.L2(0.009),
            kernel_constraint=constraints.max_norm(0.6),
            kernel_initializer='he_uniform',
            name=f'{stage_name}_conv1'
        )(x)
        x = layers.BatchNormalization(name=f'{stage_name}_bn1')(x)
        x = layers.Activation('elu', name=f'{stage_name}_elu1')(x)
        x = layers.Dropout(0.1, name=f'{stage_name}_drop1')(x)

        x = layers.Conv1D(
            32, 3, dilation_rate=dilation_rate, padding='causal',
            activation='linear',
            kernel_regularizer=regularizers.L2(0.009),
            kernel_constraint=constraints.max_norm(0.6),
            kernel_initializer='he_uniform',
            name=f'{stage_name}_conv2'
        )(x)
        x = layers.BatchNormalization(name=f'{stage_name}_bn2')(x)
        x = layers.Activation('elu', name=f'{stage_name}_elu2')(x)
        x = layers.Dropout(0.1, name=f'{stage_name}_drop2')(x)

        # Residual: 1x1 conv if dims differ
        if residual.shape[-1] != 32:
            residual = layers.Conv1D(32, 1, name=f'{stage_name}_res_conv')(residual)
        x = layers.Add(name=f'{stage_name}_add')([residual, x])
        x = layers.Activation('elu', name=f'{stage_name}_elu_out')(x)
        return x

    # Stage 1: dilation = 1
    x = dilated_stage(input_tensor, 1, f'{name_prefix}_di_s1')
    # Stage 2: dilation = 2^(window_idx + 1)
    dilation = 2 ** (window_idx + 1)
    x = dilated_stage(x, dilation, f'{name_prefix}_di_s2')
    return x


def build_hybrid_model(n_classes=12, n_channels=7, window_size=80, n_windows=4, sensor_mode='combine'):
    """
    Build the Hybrid CNN-Dilated Self-Attention model.
    Input: (batch, 1, window_size, n_channels)
    Output: (batch, n_classes) softmax probabilities
    """
    inp = layers.Input(shape=(1, window_size, n_channels), name='input')

    if sensor_mode == 'combine':
        # Slice IMU (channels 0:6) and HBC (channel 6)
        imu = layers.Lambda(lambda x: x[:, :, :, 0:6], name='slice_imu')(inp)
        cap = layers.Lambda(
            lambda x: tf.expand_dims(x[:, :, :, -1], -1), name='slice_cap'
        )(inp)

        # Permute to (batch, 80, in_chans, 1)
        imu = layers.Permute((2, 3, 1), name='permute_imu')(imu)
        cap = layers.Permute((2, 3, 1), name='permute_cap')(cap)

        # Conv blocks → each outputs (batch, 80, 1, 128)
        imu_out = conv_block(imu, in_chans=6, name_prefix='imu')
        cap_out = conv_block(cap, in_chans=1, name_prefix='cap')

        # Concatenate → (batch, 80, 1, 256)
        fused = layers.Concatenate(axis=-1, name='concat_branches')([imu_out, cap_out])

        # Squeeze spatial dim → (batch, 80, 256)
        block1 = layers.Lambda(lambda x: x[:, :, -1, :], name='squeeze_spatial')(fused)
        feat_dim = 256

    elif sensor_mode == 'imu':
        x = layers.Permute((2, 3, 1), name='permute_imu')(inp)
        x = conv_block(x, in_chans=n_channels, name_prefix='imu')
        block1 = layers.Lambda(lambda x: x[:, :, -1, :], name='squeeze_spatial')(x)
        feat_dim = 128

    elif sensor_mode == 'cap':
        x = layers.Permute((2, 3, 1), name='permute_cap')(inp)
        x = conv_block(x, in_chans=n_channels, name_prefix='cap')
        block1 = layers.Lambda(lambda x: x[:, :, -1, :], name='squeeze_spatial')(x)
        feat_dim = 128

    # Sliding windows → MHA → DilatedTCN → Dense per window → Average → Softmax
    window_outputs = []
    for i in range(n_windows):
        start_idx = i
        end_idx = window_size - n_windows + i + 1
        # Slice window
        win = layers.Lambda(
            lambda x, s=start_idx, e=end_idx: x[:, s:e, :],
            name=f'window_{i}_slice'
        )(block1)

        # MHA block
        win = mha_block(win, name_prefix=f'w{i}')

        # Dilated TCN block
        win = di_block(win, window_idx=i, name_prefix=f'w{i}')

        # Take last timestep → (batch, 32)
        win = layers.Lambda(
            lambda x: x[:, -1, :], name=f'w{i}_last_step'
        )(win)

        # Dense logits per window → (batch, n_classes)
        win = layers.Dense(
            n_classes,
            kernel_regularizer=regularizers.L2(0.5),
            name=f'w{i}_dense'
        )(win)

        window_outputs.append(win)

    # Average window logits → Softmax
    if len(window_outputs) > 1:
        avg = layers.Average(name='avg_windows')(window_outputs)
    else:
        avg = window_outputs[0]

    output = layers.Activation('softmax', name='softmax')(avg)

    model = keras.Model(inputs=inp, outputs=output, name='HybridCNN_DilatedSA')
    return model

# ──────────────────────────────────────────────
# Learning Rate Scheduler
# ──────────────────────────────────────────────

def lr_schedule(epoch, lr):
    """Decay LR by 0.5x every 50 epochs."""
    if epoch > 0 and epoch % 50 == 0:
        return lr * 0.5
    return lr

# ──────────────────────────────────────────────
# Evaluation & Visualization
# ──────────────────────────────────────────────

def evaluate_model(model, X_test, y_test_cat, y_test, le, results_dir):
    """Run full evaluation and save plots + metrics."""
    # Predictions
    y_pred_probs = model.predict(X_test, batch_size=512, verbose=1)
    y_pred = np.argmax(y_pred_probs, axis=1)

    acc = accuracy_score(y_test, y_pred)
    f1_macro = f1_score(y_test, y_pred, average='macro')
    kappa = cohen_kappa_score(y_test, y_pred)

    print(f"\n{'='*50}")
    print(f"  Accuracy:     {acc:.4f}")
    print(f"  Macro F1:     {f1_macro:.4f}")
    print(f"  Cohen Kappa:  {kappa:.4f}")
    print(f"{'='*50}\n")

    report = classification_report(
        y_test, y_pred, target_names=le.classes_, output_dict=True
    )
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(12, 10))
    sns.heatmap(
        cm, annot=True, fmt='d', cmap='Blues',
        xticklabels=le.classes_, yticklabels=le.classes_
    )
    plt.title('Confusion Matrix — Hybrid CNN-Dilated Self-Attention', fontsize=14)
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'confusion_matrix.png'), dpi=150)
    plt.close()
    print(f"[SAVED] Confusion matrix → {results_dir}/confusion_matrix.png")

    return {
        'accuracy': float(acc),
        'f1_macro': float(f1_macro),
        'cohen_kappa': float(kappa),
        'classification_report': report,
    }


def plot_learning_curves(history, results_dir):
    """Plot and save training/validation loss and accuracy curves."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Loss
    axes[0].plot(history.history['loss'], label='Train Loss', color='#1D3461')
    axes[0].plot(history.history['val_loss'], label='Val Loss', color='#1D9E75')
    axes[0].set_title('Loss Curves')
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Loss')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Accuracy
    axes[1].plot(history.history['accuracy'], label='Train Accuracy', color='#1D3461')
    axes[1].plot(history.history['val_accuracy'], label='Val Accuracy', color='#1D9E75')
    axes[1].set_title('Accuracy Curves')
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('Accuracy')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(results_dir, 'learning_curves.png'), dpi=150)
    plt.close()
    print(f"[SAVED] Learning curves → {results_dir}/learning_curves.png")

# ──────────────────────────────────────────────
# Main Training Pipeline
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='GymSense AI — Train Hybrid CNN-Dilated Self-Attention')
    parser.add_argument('--data-path', type=str, default='RecGym.csv', help='Path to RecGym.csv')
    parser.add_argument('--test-user', type=int, default=10, help='User ID to hold out for testing (1-10)')
    parser.add_argument('--sensor', type=str, default='combine', choices=['combine', 'imu', 'cap'],
                        help='Sensor mode: combine (IMU+HBC), imu, or cap')
    parser.add_argument('--epochs', type=int, default=150, help='Max training epochs')
    parser.add_argument('--batch-size', type=int, default=256, help='Training batch size')
    args = parser.parse_args()

    # Configure GPU
    gpus = configure_gpu()

    # Create output directories
    os.makedirs('models', exist_ok=True)
    os.makedirs('results', exist_ok=True)

    # Load and preprocess data
    df = load_and_filter(args.data_path)
    (X_train, y_train_cat, X_test, y_test_cat,
     y_train, y_test, sample_weights,
     scaler, le, n_classes, n_channels) = prepare_data(
        df, args.sensor, args.test_user
    )

    # Save scaler and label encoder
    joblib.dump(scaler, 'models/scaler.pkl')
    joblib.dump(le, 'models/label_encoder.pkl')
    print("[SAVED] Scaler → models/scaler.pkl")
    print("[SAVED] Label Encoder → models/label_encoder.pkl")

    # Build model (use MirroredStrategy if multiple GPUs)
    strategy = tf.distribute.MirroredStrategy() if len(gpus) > 1 else tf.distribute.get_strategy()

    with strategy.scope():
        model = build_hybrid_model(
            n_classes=n_classes,
            n_channels=n_channels,
            window_size=80,
            n_windows=4,
            sensor_mode=args.sensor,
        )
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.0001),
            loss='categorical_crossentropy',
            metrics=['accuracy'],
        )

    model.summary()

    # Callbacks
    cb_list = [
        callbacks.EarlyStopping(
            monitor='val_loss', patience=20,
            restore_best_weights=True, verbose=1
        ),
        callbacks.ModelCheckpoint(
            'models/best_model.weights.h5',
            monitor='val_accuracy', save_best_only=True,
            save_weights_only=True, verbose=1
        ),
        callbacks.LearningRateScheduler(lr_schedule, verbose=1),
    ]

    # Train
    print(f"\n[TRAIN] Starting training for up to {args.epochs} epochs ...")
    history = model.fit(
        X_train, y_train_cat,
        validation_data=(X_test, y_test_cat),
        epochs=args.epochs,
        batch_size=args.batch_size,
        sample_weight=sample_weights,
        callbacks=cb_list,
        verbose=1,
    )

    # Save full model
    model.save('models/best_model.keras')
    print("[SAVED] Full model → models/best_model.keras")

    # Evaluate
    metrics = evaluate_model(model, X_test, y_test_cat, y_test, le, 'results')

    # Plot learning curves
    plot_learning_curves(history, 'results')

    # Save training summary
    summary = {
        'sensor_mode': args.sensor,
        'test_user': args.test_user,
        'n_channels': n_channels,
        'n_classes': n_classes,
        'classes': list(le.classes_),
        'epochs_trained': len(history.history['loss']),
        'best_val_accuracy': float(max(history.history['val_accuracy'])),
        'best_val_loss': float(min(history.history['val_loss'])),
        'final_train_accuracy': float(history.history['accuracy'][-1]),
        'final_train_loss': float(history.history['loss'][-1]),
        'test_accuracy': metrics['accuracy'],
        'test_f1_macro': metrics['f1_macro'],
        'test_cohen_kappa': metrics['cohen_kappa'],
        'train_samples': int(X_train.shape[0]),
        'test_samples': int(X_test.shape[0]),
    }

    with open('results/training_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print("[SAVED] Training summary → results/training_summary.json")

    print("\n[DONE] Training complete.")


if __name__ == '__main__':
    main()
