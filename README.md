# RFID Attendance System 🚀
**Team**: Mohamed Ahmed Elazab
          Tarek Adel Elkellawy
          Mohamed Amid Younes

**Date Started**: 30/10/2024

## 📝 Project Overview
An RFID-based attendance system using ESP32, MySQL, and Flask.  
**Key Features**:
- RFID tag scanning and attendance logging
- Web portal for data visualization
- Secure API authentication

## 🛠️ Setup Instructions
1. **Clone the repo**:
   ```bash
   git clone https://github.com/your-username/rfid-attendance-system.git
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Database setup**:
   ```sql
   mysql -u root -p < schema.sql
   ```

## ✅ Milestones Conquered
- [x] Flask backend setup
- [x] MySQL database integration
- [x] API key authentication
- [x] `/api/attendance` POST endpoint

## 🎯 Next Milestones
- [ ] Deploy backend to Heroku/AWS
- [ ] Build web portal frontend
- [ ] ESP32 hardware integration
- [ ] Bulk data sync for offline mode

## 👥 Team Members
- [Mohamed Ahmed Elazab] (Backend & Database)
- [Mohamed Amid Younes] (Frontend & Web Portal)
- [Tarek Adel Elkellawy] (Hardware & ESP32)

## 📂 Project Structure
```
├── app.py               # Flask backend
├── schema.sql           # MySQL database schema
├── requirements.txt     # Python dependencies
└── README.md            # Project documentation
```

## 🔒 Security Note
**Never commit secrets** (API keys, passwords). Use `.env` files!

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/flask-2.0.1-green)
![MySQL](https://img.shields.io/badge/mysql-8.0-orange)
