# Medicine Expiry Tracker

A web application to track medicine expiry dates and manage inventory for multiple users. Never miss an expired medicine with our smart tracking system!

## 🌟 Features

- **Multi-User Support**: Each user has their own secure account with JWT authentication
- **Medicine Tracking**: Add, view, and delete medicines with expiry dates
- **Smart Status Indicators**:
  - 🟢 **Safe**: More than 30 days until expiry
  - 🟠 **Warning**: 30 days or less until expiry
  - 🔴 **Expired**: Already expired medicines
- **Days Left Counter**: Automatically calculates days remaining until expiry
- **Secure Authentication**: Password hashing and JWT tokens
- **Cloud Deployed**: Hosted on Render for 24/7 availability
- **Responsive Design**: Works on desktop and mobile devices

## 🛠 Tech Stack

### Backend

- **Flask**: Python web framework
- **SQLite**: Database for storing users and medicines
- **JWT (PyJWT)**: Secure token-based authentication
- **Gunicorn**: Production WSGI server
- **Werkzeug**: Password hashing and security utilities

### Frontend

- **HTML5**: Markup
- **CSS3**: Styling with gradient backgrounds
- **JavaScript (Vanilla)**: Dynamic functionality and API calls
- **LocalStorage**: Client-side token management

### Deployment

- **Docker**: Container orchestration
- **Render.com**: Cloud hosting platform
- **GitHub**: Version control and CI/CD integration

## 📋 Prerequisites

- Python 3.10+
- pip (Python package manager)
- Git
- Render.com account (for deployment)
- GitHub account (for version control)

## 🚀 Quick Start

### Local Development

1. **Clone the repository**

   ```bash
   git clone https://github.com/Mallesh-5577/Medicine-Exp-Tracker.git
   cd Medicine-Exp-Tracker/Backend
   ```

2. **Create and activate virtual environment**

   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database**

   ```bash
   python setup_db.py
   ```

5. **Run the application**

   ```bash
   python app.py
   ```

6. **Access the application**
   ```
   Open browser and go to: http://localhost:1000
   ```

## 📁 Project Structure

```
Medicine-Exp-Tracker/
├── Backend/
│   ├── Frontend/
│   │   ├── index.html          # Dashboard (medicines list)
│   │   ├── login.html          # Login/Signup page
│   │   ├── script.js           # Frontend JavaScript
│   │   └── style.css           # Styling
│   ├── app.py                  # Flask application & API endpoints
│   ├── setup_db.py             # Database initialization
│   ├── requirements.txt        # Python dependencies
│   ├── Procfile                # Deployment configuration
│   ├── Dockerfile              # Container configuration
│   └── docker-compose.yml      # Docker compose setup
├── .gitignore
└── README.md
```

## 🔐 API Endpoints

### Authentication

- `POST /signup` - Create new user account

  ```json
  {
    "email": "user@example.com",
    "password": "password123"
  }
  ```

- `POST /login` - Login and get JWT token
  ```json
  {
    "email": "user@example.com",
    "password": "password123"
  }
  ```
  Response: `{ "token": "eyJhbGc..." }`

### Medicine Management (Requires Token)

All requests must include header: `Authorization: Bearer <token>`

- `GET /medicines` - Get all medicines for logged-in user
- `POST /add` - Add new medicine

  ```json
  {
    "name": "Aspirin",
    "batch": "BATCH001",
    "expiry": "2025-12-31",
    "barcode": "1234567890",
    "quantity": 10
  }
  ```

- `DELETE /delete/<id>` - Delete a medicine

## 👤 User Authentication

### Sign Up

1. Click "Sign up here" on login page
2. Enter email and password
3. Password must be at least 6 characters
4. Click "Sign Up"
5. Redirect to login page

### Login

1. Enter your email and password
2. Click "Login"
3. Redirected to dashboard
4. Token saved in browser's localStorage

### Security Features

- Passwords hashed using Werkzeug
- JWT tokens expire-based validation
- User data isolation (can only see own medicines)
- CORS enabled for cross-origin requests

## 🗄 Database Schema

### Users Table

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Medicines Table

```sql
CREATE TABLE medicines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    batch TEXT NOT NULL,
    expiry TEXT NOT NULL,
    barcode TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
)
```

## 🐳 Docker Deployment

### Build and Run with Docker

```bash
cd Backend

# Build image
docker build -t medicine-tracker .

# Run container
docker run -p 1000:1000 medicine-tracker

# Or use Docker Compose
docker-compose up --build
```

Access at `http://localhost:1000`

## ☁️ Cloud Deployment (Render)

### Prerequisites

- Push code to GitHub
- Create Render account at https://render.com

### Steps

1. Create new Web Service on Render
2. Connect GitHub repository
3. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Port**: 10000
4. Deploy!

### Environment Variables (Optional)

```
SECRET_KEY=your-secure-secret-key-here
FLASK_ENV=production
```

## 📱 Usage Guide

### Adding a Medicine

1. Login to your account
2. Fill in medicine details:
   - **Medicine Name**: e.g., Aspirin
   - **Batch No**: e.g., BATCH001
   - **Expiry Date**: Select date
   - **Barcode**: e.g., 1234567890
   - **Quantity**: Number of units
3. Click "Add Medicine"

### Viewing Medicines

- Dashboard shows all your medicines
- Color-coded status:
  - Green: Safe (>30 days)
  - Orange: Warning (≤30 days)
  - Red: Expired

### Deleting a Medicine

1. Find medicine in list
2. Click "Delete" button
3. Confirmed deleted

### Logging Out

- Click "Logout" button in top-right
- Redirected to login page

## 🧪 Testing

### Test Accounts

```
Email: test@example.com
Password: password123

Email: user2@example.com
Password: test123456
```

### Manual Testing Checklist

- [ ] Signup with new email
- [ ] Login with credentials
- [ ] Add medicine with all fields
- [ ] Verify status indicators (safe/warning/expired)
- [ ] Delete medicine
- [ ] Logout and verify redirect
- [ ] Login with different account
- [ ] Verify data isolation (only see own medicines)

## 📊 Status Color Reference

| Status  | Days Left | Color     | Meaning          |
| ------- | --------- | --------- | ---------------- |
| Safe    | > 30      | 🟢 Green  | Plenty of time   |
| Warning | 0-30      | 🟠 Orange | Take action soon |
| Expired | < 0       | 🔴 Red    | Do not use       |

## 🐛 Troubleshooting

### Issue: "Cannot connect to server"

- Ensure backend is running on correct port (1000)
- Check browser console for API errors
- Verify token is saved in localStorage

### Issue: "Unauthorized" error

- Token may be expired, try logging in again
- Check Authorization header in API requests
- Clear browser cache and localStorage

### Issue: Static files not loading (CSS/JS)

- Check Flask static folder configuration
- Verify file paths in HTML
- Restart the application

### Issue: Database locked

- Only one instance of app should run
- Restart application
- Clear database if corrupted: `rm medicine_expiry.db`

## 🔒 Security Considerations

⚠️ **Before Production Deployment**:

1. Change `SECRET_KEY` in `app.py`
   ```python
   SECRET_KEY = "your-very-secure-random-key-here"
   ```
2. Enable HTTPS (Render does this automatically)
3. Set secure cookies in production
4. Use environment variables for secrets
5. Add rate limiting for login attempts
6. Implement password strength requirements

## 📝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📈 Future Enhancements

- [ ] Email notifications for expiring medicines
- [ ] Medicine categories/tags
- [ ] Barcode scanning
- [ ] Expiry date alerts via SMS
- [ ] Admin dashboard for multi-store management
- [ ] Medicine search and filters
- [ ] Export medicines list to PDF/CSV
- [ ] Dark mode theme
- [ ] Two-factor authentication
- [ ] Medicine usage history

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👨‍💻 Author

**Mallesh-5577** - [GitHub Profile](https://github.com/Mallesh-5577)

## 🔗 Links

- **Live Demo**: https://medicine-exp-tracker-7.onrender.com
- **GitHub Repository**: https://github.com/Mallesh-5577/Medicine-Exp-Tracker
- **Render Deployment**: https://render.com

## 📞 Support

For issues, questions, or suggestions:

1. Open an issue on GitHub
2. Check existing issues for solutions
3. Include error messages and steps to reproduce

## 🙏 Acknowledgments

- Flask documentation
- Render.com hosting
- JWT for secure authentication
- Community feedback and contributions

---

**Last Updated**: February 2026  
**Status**: ✅ Production Ready
