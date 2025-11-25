# 🔧 McAfee SIEM Alarm Editor v2.0.0

**Advanced Customer & Rule Management Web Application for McAfee SIEM**

> 🌟 **Complete Project Implementation** - Full-stack web application with React frontend and Flask backend

## 🏗️ Project Architecture

This is a complete, production-ready web application consisting of:

- **🖥️ Frontend**: React 18 + Vite + Tailwind CSS
- **⚙️ Backend**: Python Flask + SQLAlchemy + SQLite
- **📊 Features**: Customer management, XML processing, rule-alarm analysis
- **🔄 API**: RESTful endpoints with full CRUD operations

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ (with venv support)
- Node.js 16+ and npm
- Git

### 1. Clone and Setup Backend

```bash
# Clone the repository
git clone <your-repo-url>
cd Trellix-Alarm-MNGT-WEB

# Start the backend (auto-installs dependencies)
./start-backend.sh
```

The Flask API will be running at `http://localhost:5000`

### 2. Setup and Start Frontend

```bash
# In a new terminal, navigate to frontend
cd frontend

# Start the frontend (auto-installs dependencies)
./start-frontend.sh
```

The React app will be running at `http://localhost:3000`

### 3. Access the Application

Open your browser and go to `http://localhost:3000` to start using the application.

## 🎯 Key Features in v2.0.0

### 👥 Customer Management
- **Multi-customer support** with dedicated workspaces
- **Customer profiles** with metadata and file associations
- **Secure file isolation** per customer
- **Customer statistics** and activity tracking

### 📋 Rule Management & Analysis
- **Rule.xml parsing** with full schema validation
- **Interactive rule browser** with search and filtering
- **Rule-to-alarm mapping** visualization
- **Automatic alarm generation** from rules
- **Severity-based filtering** and batch operations

### 🔗 Rule-Alarm Relationship Management
- **Automatic relationship detection** between rules and alarms
- **Coverage analysis** and gap identification
- **Bulk alarm generation** from selected rules
- **Validation reports** with detailed error analysis

### ✅ Enhanced Validation
- **Schema-based validation** for both rule.xml and alarm.xml
- **Real-time error reporting** with line-level precision
- **Relationship validation** between rule SigIDs and alarm matchValues
- **Import/export validation** with user-friendly error messages

## 📁 Project Structure

```
Trellix-Alarm-MNGT-WEB/
├── 🐍 Backend (Flask API)
│   ├── main.py                     # Flask application entry point
│   ├── requirements.txt            # Python dependencies
│   ├── start-backend.sh           # Backend startup script
│   ├── src/
│   │   ├── models/
│   │   │   └── customer.py        # SQLAlchemy models
│   │   ├── routes/
│   │   │   ├── customer.py        # Customer API endpoints
│   │   │   ├── rule.py           # Rule API endpoints
│   │   │   ├── alarm.py          # Alarm API endpoints
│   │   │   └── analysis.py       # Analysis API endpoints
│   │   └── utils/
│   │       └── xml_utils.py       # XML processing utilities
│   ├── database/                  # SQLite database
│   ├── uploads/                   # Customer file uploads
│   ├── static/                    # Built frontend files
│   └── venv/                      # Python virtual environment
├── ⚛️ Frontend (React SPA)
│   ├── package.json               # Node.js dependencies
│   ├── vite.config.js            # Vite configuration
│   ├── tailwind.config.js        # Tailwind CSS config
│   ├── start-frontend.sh         # Frontend startup script
│   ├── src/
│   │   ├── main.jsx              # React entry point
│   │   ├── App.jsx               # Main application component
│   │   ├── components/
│   │   │   ├── layout/           # Layout components
│   │   │   ├── pages/            # Page components
│   │   │   └── ui/               # Reusable UI components
│   │   ├── hooks/                # Custom React hooks
│   │   ├── lib/                  # API client and utilities
│   │   └── styles/               # CSS and styling
│   └── public/                   # Static assets
└── 📚 Legacy/
    └── alarm_editor.py           # Original PyQt desktop app
```

## 🎯 Key Features

### Customer Management Tab
- **Create/Edit/Delete** customers with metadata
- **Import rule and alarm files** with validation
- **Export customer files** individually or in bulk
- **File validation** with detailed error reporting
- **Customer statistics** and activity overview

### Rule Management Tab
- **Interactive rule table** with severity color coding
- **Advanced search and filtering** by rule ID, message, or SigID
- **Rule details viewer** with complete metadata
- **Batch alarm generation** from selected rules
- **Rule validation** and error reporting

### Alarm Management Tab (Enhanced)
- **Traditional alarm editing** with improved UI
- **Integration with customer files**
- **Auto-generated alarms** from rules
- **Enhanced property editor** with validation

### Rule-Alarm Mapping Tab
- **Relationship analysis** between rules and alarms
- **Coverage percentage** calculation
- **Unmatched rules/alarms** identification
- **Automatic alarm generation** with severity filtering
- **Detailed mapping reports**

## 🔗 API Endpoints

### Customer Management
- `GET /api/customers` - List all customers
- `POST /api/customers` - Create new customer
- `GET /api/customers/{id}` - Get customer details
- `PUT /api/customers/{id}` - Update customer
- `DELETE /api/customers/{id}` - Delete customer
- `POST /api/customers/{id}/files/upload` - Upload XML files

### Rule Management
- `GET /api/customers/{id}/rules` - List customer rules
- `GET /api/customers/{id}/rules/search` - Search rules
- `POST /api/customers/{id}/rules/generate-alarms` - Generate alarms

### Alarm Management
- `GET /api/customers/{id}/alarms` - List customer alarms
- `POST /api/customers/{id}/alarms` - Create alarm
- `PUT /api/customers/{id}/alarms/{alarm_id}` - Update alarm
- `DELETE /api/customers/{id}/alarms/{alarm_id}` - Delete alarm

### Analysis
- `GET /api/customers/{id}/analysis/coverage` - Coverage analysis
- `POST /api/customers/{id}/analysis/generate-missing` - Generate missing alarms
- `POST /api/customers/{id}/analysis/detect-relationships` - Detect relationships

## 🛠️ Development Workflow

### Backend Development
```bash
# Activate virtual environment
source venv/bin/activate

# Install new dependencies
pip install package_name
pip freeze > requirements.txt

# Run with auto-reload
python main.py
```

### Frontend Development
```bash
cd frontend

# Install new dependencies
npm install package-name

# Run development server with hot reload
npm run dev

# Build for production
npm run build
```

### Database Management
The SQLite database is automatically created when you first run the application. Tables include:
- `customers` - Customer information
- `customer_files` - Uploaded file metadata
- `rules` - Parsed rule data
- `alarms` - Alarm configurations
- `rule_alarm_relationships` - Rule-alarm mappings
- `validation_logs` - Validation history

## 📖 Usage Guide

### 1. Customer Management
1. **Create a Customer**: Click "New Customer" and fill in the details
2. **Import Files**: Use "Import Rule File" and "Import Alarm File" buttons
3. **Validate Files**: Use validation buttons to check file integrity
4. **Export Files**: Export customer files when needed

### 2. Rule Analysis
1. **Select a Customer** with a loaded rule file
2. **Browse Rules** in the Rule Management tab
3. **Search/Filter** rules by various criteria
4. **View Details** by double-clicking or using context menu
5. **Generate Alarms** from selected rules

### 3. Alarm Generation
1. **Select Rules** in the Rule Management tab
2. **Use "Generate Alarms"** button for selected rules
3. **Or use Auto-Generation** in the Mapping tab with severity filters
4. **Review Generated Alarms** in the Alarm Management tab

### 4. Relationship Analysis
1. **Load both rule and alarm files** for a customer
2. **Use "Analyze Relationships"** in the Mapping tab
3. **Review coverage** and identify gaps
4. **Generate missing alarms** automatically

## 🔍 Validation Features

### Rule File Validation
- ✅ XML structure validation
- ✅ Required element checking
- ✅ Severity range validation (0-100)
- ✅ SigID presence verification
- ✅ CDATA content parsing

### Alarm File Validation
- ✅ XML structure validation
- ✅ Required attribute checking
- ✅ Condition data validation
- ✅ Action configuration verification
- ✅ Boolean value validation

### Relationship Validation
- ✅ SigID to matchValue mapping
- ✅ Coverage analysis
- ✅ Orphaned rule/alarm detection
- ✅ Format consistency checking

## 📊 Schema Compliance

The application validates against McAfee SIEM XML schemas:

### Rule.xml Schema
```xml
<nitro_policy>
  <rules count="N">
    <rule>
      <id>XX-XXXXXXX</id>
      <message>Rule Name</message>
      <severity>0-100</severity>
      <text><![CDATA[
        <ruleset id="XX-XXXXXXX">
          <property>
            <n>sigid</n>
            <value>XXXXXXX</value>
          </property>
        </ruleset>
      ]]></text>
    </rule>
  </rules>
</nitro_policy>
```

### Alarm.xml Schema
```xml
<alarms>
  <alarm name="Alarm Name" minVersion="11.6.14">
    <alarmData>
      <severity>0-100</severity>
    </alarmData>
    <conditionData>
      <matchField>DSIDSigID</matchField>
      <matchValue>XX|XXXXXXX</matchValue>
    </conditionData>
    <actions>
      <actionData>
        <actionType>0</actionType>
        <actionProcess>1</actionProcess>
      </actionData>
    </actions>
  </alarm>
</alarms>
```

## 🔧 Advanced Features

### Automatic Alarm Generation
- **Rule-based generation** with configurable templates
- **Severity filtering** for targeted generation
- **Batch processing** for multiple rules
- **Validation integration** for generated alarms

### Customer Isolation
- **Separate workspaces** per customer
- **File versioning** and backup
- **Access control** and audit trails
- **Data integrity** protection

### Error Handling
- **Graceful error recovery** with detailed messages
- **Validation warnings** vs. critical errors
- **User-friendly error dialogs** with actionable advice
- **Comprehensive logging** for troubleshooting

## 🐛 Troubleshooting

### Common Issues
1. **Import Validation Fails**: Check XML structure and required elements
2. **Rule Parsing Errors**: Verify CDATA content and property structure
3. **Relationship Mismatches**: Ensure SigID format consistency
4. **File Access Issues**: Check file permissions and paths

### Debug Mode
Enable debug logging by setting the log level in the application:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 📝 Version History

### v2.0.0 (Current)
- ✨ Customer management system
- ✨ Rule parsing and analysis
- ✨ Automatic alarm generation
- ✨ Enhanced validation engine
- ✨ Tabbed interface redesign

### v1.5.1 (Previous)
- 🔧 Basic alarm editing
- 🔧 XML validation
- 🔧 Property editor

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the validation reports for detailed error information 
