# 💧 RFID-Based Smart Water Supply Monitoring & Billing System

A full-featured **Streamlit web application** that simulates an **IoT-enabled smart water distribution system**.
This project enables **RFID-based user authentication**, **real-time water usage tracking**, **dynamic billing**, and **advanced analytics**.

---

## 🚀 Live Demo

👉 https://vzspd5zsrekxjayvb5qxne.streamlit.app/

---

## 📌 Features

### 🔐 RFID-Based User System

* Unique RFID ID for each user
* Simulated RFID scan (manual + dropdown)
* User authentication with profile display

### 💧 Water Usage Monitoring

* Track water consumption (liters)
* Real-time/manual usage input
* Historical data (daily, weekly, monthly)

### 💰 Smart Billing System

* Slab-based billing (like electricity system)
* Example:

  * 0–100L → ₹2/L
  * 101–500L → ₹5/L
  * Above 500L → ₹10/L
* Detailed bill breakdown
* Download bill as **PDF & CSV**

### 📊 Dashboard & Analytics

* Interactive charts using Plotly
* Daily & monthly consumption trends
* User-wise usage comparison
* Water conservation insights

### 🛠️ Admin Panel

* Add / Edit / Delete users
* Assign RFID IDs
* Update billing rates dynamically
* Monitor overall system usage

### 🚨 Alerts & Notifications

* Threshold-based usage alerts
* Abnormal usage detection (leak detection)
* Simulated SMS/email warnings

### 🤖 Advanced Features

* Water usage prediction using Machine Learning
* Leak detection logic
* Personalized water-saving recommendations
* Role-based login (Admin/User)
* Dark mode UI

---

## 🧠 Tech Stack

* **Frontend & Backend:** Streamlit
* **Language:** Python
* **Database:** SQLite
* **Data Processing:** Pandas
* **Visualization:** Plotly
* **Machine Learning:** Scikit-learn
* **PDF Generation:** ReportLab

---

## 📂 Project Structure

```bash
rfid_smart_water_app/
│── app.py
│── database.py
│── utils.py
│── auth.py
│── requirements.txt
│── README.md
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository

```bash
git clone https://github.com/shreya975/rfid_smart_water_app.git
cd rfid_smart_water_app
```

### 2️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Run the application

```bash
python -m streamlit run app.py
```

---

## 🔑 Demo Credentials

### 👨‍💼 Admin

* Username: `admin`
* Password: `admin123`

### 👩‍💻 User

* Username: `shreya`
* Password: `user123`

---

## 📈 Future Enhancements

* 🔌 Real IoT sensor integration (ESP32, flow sensors)
* 📱 SMS/email alerts (Twilio integration)
* 📷 QR-based authentication
* ☁️ Cloud database (Firebase / AWS)
* 📊 Advanced ML models for forecasting
* 🌍 Smart city dashboards

---

## 🤝 Contributing

Contributions are welcome!
Feel free to fork this repository and submit a pull request.

---

## 📜 License

This project is open-source and available under the **MIT License**.

---

## 💡 Author

**Shreya Mahajan**
📌 Passionate about Data Science 
