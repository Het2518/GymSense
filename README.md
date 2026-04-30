# 🏋️ GymSense AI

![GymSense AI Banner](https://img.shields.io/badge/GymSense-AI_Workout_Analytics-orange?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat-square&logo=fastapi)
![React](https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB)
![TensorFlow](https://img.shields.io/badge/TensorFlow-%23FF6F00.svg?style=flat-square&logo=TensorFlow&logoColor=white)

**GymSense AI** is a state-of-the-art, full-stack fitness analytics platform that bridges the gap between raw wearable sensor data and actionable fitness coaching. By leveraging a custom **Hybrid CNN-Dilated Self-Attention Keras Model**, GymSense performs highly accurate real-time activity recognition on raw IMU (Inertial Measurement Unit) and electrostatic sensor data.

---

## 🎯 Objective & Description

The primary objective of GymSense is to eliminate the need for manual workout tracking while simultaneously providing professional-grade biomechanical feedback. 

Instead of relying on users to log sets, reps, and weights, GymSense ingests 7-channel sensor telemetry (Accelerometer `A_x, A_y, A_z`, Gyroscope `G_x, G_y, G_z`, and Electrostatic `C_1`) and passes it through an advanced AI pipeline. 

### Core Capabilities:
- **🧠 Advanced Activity Recognition:** Automatically classifies 11 different workout movements (e.g., Squats, Bench Press, Leg Press, Rope Skipping, Running, etc.) using our pre-trained Keras model.
- **⏱️ Automated Rep Counting & Tempo Scoring:** Uses sophisticated peak-detection and run-length encoding to count precise repetitions and evaluate the consistency and control of user pacing (Tempo Score).
- **🤖 LLM Generative Coaching:** Integrates with the **Groq API** (Llama 3 70B) to generate highly personalized coaching insights based on the user's uploaded biomechanical data and physical profile.
- **📊 Real-Time Simulation:** Includes a dynamic simulation engine that generates real-time synthetic human kinematics, allowing developers and users to test the pipeline without physical sensors.
- **📄 Automated PDF Reports:** Generates structured, visually rich PDF reports summarizing the session, complete with SVG tempo gauges and exercise timelines.

---

## 🚀 Tech Stack

**Frontend:**
* React 18 & Vite
* TailwindCSS (Styling)
* Framer Motion (Micro-animations)
* Recharts (Real-time data visualization)
* Three.js (3D aesthetic backgrounds)

**Backend & AI Pipeline:**
* FastAPI (High-performance async Python backend)
* MongoDB (Motor async driver for session/user storage)
* TensorFlow & Keras (Model inference & prediction)
* Groq SDK (Generative LLM coaching)
* xhtml2pdf & Jinja2 (PDF generation)

---

## ⚙️ Installation & Local Setup

### Prerequisites
- Node.js (v18+)
- Python (v3.10+)
- MongoDB Atlas Cluster (or local instance)
- Groq API Key (for LLM Coaching)

### 1. Clone the Repository
```bash
git clone https://github.com/Het2518/GymSense.git
cd GymSense
```

### 2. Backend Setup
1. Open a new terminal and navigate to the backend:
   ```bash
   cd backend
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Set up environment variables. Create a `.env` file in the root project directory:
   ```env
   MONGODB_URI=mongodb+srv://<user>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
   JWT_SECRET=your_super_secret_jwt_string_here
   GROQ_API_KEY=gsk_your_groq_api_key_here
   ```
4. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### 3. Frontend Setup
1. Open a second terminal and navigate to the frontend:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
4. Open your browser to `http://localhost:3000` (or `5173`).

---

## 📖 How to Use the Application

1. **Authentication:** Create an account and log in. Your session is securely maintained via JWT tokens.
2. **Setup Profile:** Navigate to the **Settings** page to input your physical profile (height, weight, goals, experience). The AI Coach uses this context to personalize feedback.
3. **Upload Sensor Data:** Go to the **Analyze (Upload)** page and drop your raw `.csv` IMU log. The system will automatically chunk the data, run inference, count reps, and evaluate your tempo.
4. **Real-Time Simulation:** Don't have a sensor? Go to the **Simulate** page (the Zap icon). Select a workout class, hit play, and watch the platform generate real-time synthetic kinematics mimicking human movement. Once finished, click *Analyze Simulation* to pipe it straight into the AI.
5. **Review Reports:** After a successful analysis, you are routed to the **History/Results** page. Here you can read your Groq-powered AI coaching feedback and download your automated PDF Session Report.

---

## 🛠️ Production Deployment
This architecture is specifically optimized for cloud deployments:
- **Frontend:** Fully compatible with [Vercel](https://vercel.com). Just connect your GitHub repo and set the `VITE_API_URL` environment variable to point to your live backend.
- **Backend:** Optimized for [Render](https://render.com) using the included `render.yaml` blueprint. The TensorFlow inference pipeline includes custom manual micro-batching to operate securely within Render's Free Tier 512MB RAM limit without crashing.

---

*Built with ❤️ for the future of biomechanical tracking.*
