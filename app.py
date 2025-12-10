from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, get_flashed_messages
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
import os
import psycopg2
from psycopg2 import pool
from datetime import datetime, timedelta
import uuid
import traceback
from dotenv import load_dotenv

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import time
import random
import string
import requests
import json
from requests.auth import HTTPBasicAuth

load_dotenv()

# Application URL Configuration (for email links)
APP_URL = os.environ.get('APP_URL', 'https://advancedentalclinic.me')

# WhatsApp API Configuration
WHATSAPP_API_URL = os.environ.get('WHATSAPP_API_URL', 'https://graph.facebook.com/v17.0/')
META_ACCESS_TOKEN = os.environ.get('META_ACCESS_TOKEN', '')
WHATSAPP_PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')

# =============================================================================
# COLUMN CONSTANTS FOR TAXI_REQUESTS TABLE (30 columns)
# =============================================================================
# Standard column indices for consistent indexing across different devices
ID = 0
EMP_CODE = 1
EMPLOYEE_NAME = 2
EMPLOYEE_EMAIL = 3
EMPLOYEE_PHONE = 4
DEPARTMENT = 5
FROM_LOCATION = 6
TO_LOCATION = 7
TRAVEL_DATE = 8
TRAVEL_TIME = 9
PURPOSE = 10
PASSENGERS = 11
STATUS = 12
MANAGER_EMAIL = 13
HOD_RESPONSE = 14
HOD_APPROVAL_DATE = 15
ADMIN_RESPONSE = 16
TAXI_DETAILS = 17
SUBMISSION_DATE = 18
ADMIN_RESPONSE_DATE = 19
CREATED_AT = 20
ASSIGNED_COST = 21
TYPE_OF_RIDE = 22
VEHICLE_COMPANY = 23
VEHICLE_TYPE = 24
VEHICLE_NUMBER = 25
RETURNING_RIDE = 26
RETURN_FROM_LOCATION = 27
RETURN_TO_LOCATION = 28
RETURN_TIME = 29

# Column name to index mapping
COLUMN_INDEX_MAP = {
    'id': ID, 'emp_code': EMP_CODE, 'employee_name': EMPLOYEE_NAME,
    'employee_email': EMPLOYEE_EMAIL, 'employee_phone': EMPLOYEE_PHONE,
    'department': DEPARTMENT, 'from_location': FROM_LOCATION,
    'to_location': TO_LOCATION, 'travel_date': TRAVEL_DATE,
    'travel_time': TRAVEL_TIME, 'purpose': PURPOSE, 'passengers': PASSENGERS,
    'status': STATUS, 'manager_email': MANAGER_EMAIL, 'hod_response': HOD_RESPONSE,
    'hod_approval_date': HOD_APPROVAL_DATE, 'admin_response': ADMIN_RESPONSE,
    'taxi_details': TAXI_DETAILS, 'submission_date': SUBMISSION_DATE,
    'admin_response_date': ADMIN_RESPONSE_DATE, 'created_at': CREATED_AT,
    'assigned_cost': ASSIGNED_COST, 'type_of_ride': TYPE_OF_RIDE,
    'vehicle_company': VEHICLE_COMPANY, 'vehicle_type': VEHICLE_TYPE,
    'vehicle_number': VEHICLE_NUMBER, 'returning_ride': RETURNING_RIDE,
    'return_from_location': RETURN_FROM_LOCATION, 'return_to_location': RETURN_TO_LOCATION,
    'return_time': RETURN_TIME
}

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', '4d0e7ea4f024d1114f9909383ed0e3ec51bd0a13e9c63daf97b1172eb1b8fffc')

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

# PostgreSQL Configuration - Use environment variables with fallbacks
app.config['DB_CONFIG'] = {
    'dbname': os.environ.get('DB_NAME', 'postgres'),
    'user': os.environ.get('DB_USER', 'postgres'),
    'password': os.environ.get('DB_PASSWORD', 'postgres'),
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': os.environ.get('DB_PORT', '5432')
}

db_pool = pool.SimpleConnectionPool(1, 20, **app.config['DB_CONFIG'])

# Debug: Print database configuration
print(f"🔍 Database Configuration:")
print(f"   Host: {app.config['DB_CONFIG']['host']}")
print(f"   Port: {app.config['DB_CONFIG']['port']}")
print(f"   Database: {app.config['DB_CONFIG']['dbname']}")
print(f"   User: {app.config['DB_CONFIG']['user']}")
print(f"   Password: {'*' * len(app.config['DB_CONFIG']['password'])}")

# Flask Mail Configuration - Using environment variables
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', '172.19.0.112')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '25'))
app.config['MAIL_USE_TLS'] = os.environ.get('USE_TLS', 'False').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'AskHRNotification@nvtpower.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('FROM_MAIL', 'DomesticFlightBookingSystem@nvtpower.com')
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_DEBUG'] = True
app.config['MAIL_SUPPRESS_SEND'] = False
app.config['MAIL_ASCII_ATTACHMENTS'] = False

EMAIL_MODE = 'production'  # Force production mode - always send to actual recipients

# Email Configuration Status
EMAIL_CONFIGURED = (
    app.config['MAIL_SERVER'] and
    app.config['MAIL_USERNAME'] and
    app.config['MAIL_DEFAULT_SENDER']
)

# Debug: Print email configuration
print(f"📧 Email Configuration:")
print(f"   Server: {app.config['MAIL_SERVER']}")
print(f"   Port: {app.config['MAIL_PORT']}")
print(f"   Username: {app.config['MAIL_USERNAME']}")
print(f"   From: {app.config['MAIL_DEFAULT_SENDER']}")
print(f"   Use TLS: {app.config['MAIL_USE_TLS']}")
print(f"   Mode: {EMAIL_MODE}")
print(f"   Configured: {EMAIL_CONFIGURED}")

# Debug: Print WhatsApp configuration
print(f"📱 WhatsApp Configuration:")
print(f"   API URL: {WHATSAPP_API_URL}")
print(f"   Access Token: {'*' * 20 if META_ACCESS_TOKEN else 'NOT SET'}")
print(f"   Phone Number ID: {WHATSAPP_PHONE_NUMBER_ID if WHATSAPP_PHONE_NUMBER_ID else 'NOT SET'}")
print(f"   Configured: {bool(META_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID)}")

# Session Configuration
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

mail = Mail(app)

# SAP API Configuration
SAP_CONFIG = {
    'username': os.environ.get('SAP_USERNAME', 'api_user@navitasysi'),
    'password': os.environ.get('SAP_PASSWORD', 'api@1234'),
    'base_url': os.environ.get('SAP_BASE_URL', 'https://api44.sapsf.com/odata/v2/')
}

# Simple in-memory cache for SAP payloads to avoid redundant calls
SAP_CACHE_TTL_SECONDS = int(os.environ.get('SAP_CACHE_TTL_SECONDS', '600'))
SAP_CACHE = {
    'manager_contact': {},
    'employee_details': {},
    'actual_manager': {}
}
SAP_REFRESH_TTL_SECONDS = int(os.environ.get('SAP_REFRESH_TTL_SECONDS', str(SAP_CACHE_TTL_SECONDS)))

SAP_EMPJOB_SELECT_FIELDS = ",".join([
    "userId",
    "managerId",
    "division",
    "divisionNav/name",
    "location",
    "locationNav/name",
    "department",
    "departmentNav/name",
    "employmentNav/personNav/dateOfBirth",
    "employmentNav/personNav/personalInfoNav/firstName",
    "employmentNav/personNav/personalInfoNav/middleName",
    "employmentNav/personNav/personalInfoNav/lastName",
    "employmentNav/personNav/emailNav/emailAddress",
    "employmentNav/personNav/emailNav/isPrimary",
    "employmentNav/personNav/emailNav/emailTypeNav/picklistLabels/label",
    "employmentNav/personNav/phoneNav/phoneNumber",
    "employmentNav/personNav/phoneNav/phoneTypeNav/picklistLabels/label",
    "managerUserNav/defaultFullName"
])

SAP_EMPJOB_EXPAND_FIELDS = ",".join([
    "divisionNav",
    "locationNav",
    "departmentNav",
    "managerUserNav",
    "employmentNav/personNav/personalInfoNav",
    "employmentNav/personNav/emailNav",
    "employmentNav/personNav/emailNav/emailTypeNav/picklistLabels",
    "employmentNav/personNav/phoneNav",
    "employmentNav/personNav/phoneNav/phoneTypeNav/picklistLabels"
])


def _get_cached_value(bucket, key):
    """Return cached value if it exists and is still fresh."""
    bucket_cache = SAP_CACHE.get(bucket, {})
    entry = bucket_cache.get(key)
    if not entry:
        return None

    age = time.time() - entry['timestamp']
    if age < SAP_CACHE_TTL_SECONDS:
        return entry['value']

    # Expired entry – remove it to keep cache tidy
    bucket_cache.pop(key, None)
    return None


def _set_cached_value(bucket, key, value):
    """Store value in cache with current timestamp."""
    SAP_CACHE.setdefault(bucket, {})
    SAP_CACHE[bucket][key] = {
        'value': value,
        'timestamp': time.time()
    }


def build_empjob_url(emp_code, select_clause=None, expand_clause=None, order_by=True):
    """Construct a trimmed EmpJob query URL."""
    select_part = select_clause or SAP_EMPJOB_SELECT_FIELDS
    expand_part = expand_clause or SAP_EMPJOB_EXPAND_FIELDS
    base_url = (
        f"{SAP_CONFIG['base_url']}EmpJob"
        f"?$select={select_part}"
        f"&$expand={expand_part}"
        f"&$filter=userId eq '{emp_code}'"
        f"&$format=json"
    )
    if order_by:
        base_url += "&$orderby=employmentNav/startDate"
    return base_url

# Department-specific Manager Mapping
DEPARTMENT_MANAGER_MAPPING = {
    'Industrial Engineering': {
        'manager_id': '9025802',
        'manager_name': 'Shivam Chaturvedi',
        'manager_email': 'shivam.chaturvedi@nvtpower.com',
        'manager_phone': '9975436603'
    },
    'Maintenance': {
        'manager_id': '9013753',
        'manager_name': 'Sudarshan Kumar',
        'manager_email': 'sudarshan.kumar@nvtpower.com',
        'manager_phone': '9466027711'
    },
    'Engineering': {
        'manager_id': '9013753',
        'manager_name': 'Sudarshan Kumar',
        'manager_email': 'sudarshan.kumar@nvtpower.com',
        'manager_phone': '9466027711'
    },
    'Industrial Relations': {
        'manager_id': '9017113',
        'manager_name': 'Tribhuvan Agnihotri',
        'manager_email': 'tribhuvan.agnihotri@nvtpower.com',
        'manager_phone': '9871908963'
    },
    'Human Resource': {
        'manager_id': '9023422',
        'manager_name': 'Mohit Agarwal',
        'manager_email': 'mohit.agarwal@nvtpower.com',
        'manager_phone': '7743967028'
    },
    'Admin': {
        'manager_id': '9022761',
        'manager_name': 'Nitika Arora',
        'manager_email': 'nitika.arora@nvtpower.com',
        'manager_phone': '9765499226'
    },
    'Information Technology': {
        'manager_id': '9024436',
        'manager_name': 'Ankur Tandon',
        'manager_email': 'ankur.tandon@nvtpower.com',
        'manager_phone': '9871908963'
    },
    'Finance & Accounts': {
        'manager_id': '9024436',
        'manager_name': 'Ankur Tandon',
        'manager_email': 'ankur.tandon@nvtpower.com',
        'manager_phone': '9871908963'
    },
    'Central Warehouse and Store': {
        'manager_id': '9024436',
        'manager_name': 'Ankur Tandon',
        'manager_email': 'ankur.tandon@nvtpower.com',
        'manager_phone': '9871908963'
    },
    'Central Warehouse Store': {
        'manager_id': '9024436',
        'manager_name': 'Ankur Tandon',
        'manager_email': 'ankur.tandon@nvtpower.com',
        'manager_phone': '9871908963'
    },
    'Production Planning & Control': {
        'manager_id': '9024436',
        'manager_name': 'Ankur Tandon',
        'manager_email': 'ankur.tandon@nvtpower.com',
        'manager_phone': '9871908963'
    },
    'Warranty': {
        'manager_id': '9024982',
        'manager_name': 'V G Padmanabhan',
        'manager_email': 'vg.padmanabhan@nvtpower.com',
        'manager_phone': '9952099233'
    },
    'Security': {
        'manager_id': '9025421',
        'manager_name': 'Rajan Vashisht',
        'manager_email': 'rajan.vashisht@nvtpower.com',
        'manager_phone': '9915591935'
    },
    'Customer Service': {
        'manager_id': '9023649',
        'manager_name': 'Jayesh Sinha',
        'manager_email': 'jayesh.sinha@nvtpower.com',
        'manager_phone': '8383010034'
    },
    'Project Management': {
        'manager_id': '9023418',
        'manager_name': 'Nishant Sharma',
        'manager_email': 'nishant.sharma@nvtpower.com',
        'manager_phone': '7419990385'
    },
    'Management': {
        'manager_id': '9017113',
        'manager_name': 'Tribhuvan Agnihotri',
        'manager_email': 'tribhuvan.agnihotri@nvtpower.com',
        'manager_phone': '9871908963'
    },
    'Production': {
        'manager_id': '9017113',
        'manager_name': 'Tribhuvan Agnihotri',
        'manager_email': 'tribhuvan.agnihotri@nvtpower.com',
        'manager_phone': '9871908963'
    },
    'Quality': {
        'manager_id': '9022826',
        'manager_name': 'Pawan Tyagi',
        'manager_email': 'pawan.tyagi@nvtpower.com',
        'manager_phone': '+919765497863'
    },
    'Environment Health & Safety': {
        'manager_id': '9025421',
        'manager_name': 'Rajan Vashisht',
        'manager_email': 'rajan.vashisht@nvtpower.com',
        'manager_phone': '9915591935'
    },
    'Technical Service & Infrastructure': {
        'manager_id': '9017113',
        'manager_name': 'Tribhuvan Agnihotri',
        'manager_email': 'tribhuvan.agnihotri@nvtpower.com',
        'manager_phone': '9871908963'
    },
    'Material Controlling': {
        'manager_id': '9023422',
        'manager_name': 'Mohit Agarwal',
        'manager_email': 'mohit.agarwal@nvtpower.com',
        'manager_phone': '7743967028'
    },
    'Business Excellence': {
        'manager_id': '9017113',
        'manager_name': 'Tribhuvan Agnihotri',
        'manager_email': 'tribhuvan.agnihotri@nvtpower.com',
        'manager_phone': '9871908963'
    },
    'COE': {
        'manager_id': '9025857',
        'manager_name': 'Shivam Chaturvedi',
        'manager_email': 'shivam.chaturvedi@nvtpower.com',
        'manager_phone': '9975436603'
    },
    'Purchase': {
        'manager_id': '9024436',
        'manager_name': 'Ankur Tandon',
        'manager_email': 'ankur.tandon@nvtpower.com',
        'manager_phone': '919871908963'
    },
    'Legal & Company Secretary': {
        'manager_id': '9024785',
        'manager_name': 'Vinod Kumar',
        'manager_email': 'vinod.kumar@nvtpower.com',
        'manager_phone': '9811772557'
    },
    'Expats': {
        'manager_id': '9022761',
        'manager_name': 'Nitika Arora',
        'manager_email': 'nitika.arora@nvtpower.com',
        'manager_phone': '9765499226'
    }
}

MANESAR_DEPARTMENTS_FOR_SHIVAM = {
    'production',
    'maintenance',
    'engineering',
    'center of excellence',
    'industrial engineering',
    'technical project management'
}

MANESAR_DEPARTMENTS_FOR_MANOJ = {
    'quality'
}

MANESAR_DEPARTMENTS_FOR_ANKUR = {
    'purchase',
    'production planning & control',
    'central warehouse store'
}

SHIVAM_MANAGER_INFO = {
    'manager_id': '9025802',
    'manager_name': 'Shivam Chaturvedi',
    'manager_email': 'shivam.chaturvedi@nvtpower.com',
    'manager_phone': '9975436603'
}

MANOJ_MANAGER_INFO = {
    'manager_id': '9012706',
    'manager_name': 'Manoj Saini',
    'manager_email': 'manoj.saini@nvtpower.com',
    'manager_phone': '9871908963'
}

ANKUR_MANAGER_INFO = {
    'manager_id': '9024436',
    'manager_name': 'Ankur Tandon',
    'manager_email': 'ankur.tandon@nvtpower.com',
    'manager_phone': '9871908963'
}

TRIBHUVAN_MANAGER_INFO = {
    'manager_id': '9017113',
    'manager_name': 'Tribhuvan Agnihotri',
    'manager_email': 'tribhuvan.agnihotri@nvtpower.com',
    'manager_phone': '9871908963'
}

RAJAN_MANAGER_INFO = {
    'manager_id': '9025421',
    'manager_name': 'Rajan Vashisht',
    'manager_email': 'rajan.vashisht@nvtpower.com',
    'manager_phone': '9915591935'
}

DEPARTMENT_MANAGER_MAPPING_LOWER = {
    name.lower(): manager_info for name, manager_info in DEPARTMENT_MANAGER_MAPPING.items()
}


def get_department_manager(department_name):
    """Return a copy of the department manager mapping, case-insensitive."""
    if not department_name:
        return None
    dept_key = department_name.strip().lower()
    manager_info = DEPARTMENT_MANAGER_MAPPING_LOWER.get(dept_key)
    if manager_info:
        return {**manager_info}
    return None


def set_manager_fields(target, manager_info):
    """Utility to populate manager fields on the target dictionary."""
    target['manager_id'] = manager_info.get('manager_id', '')
    target['manager_name'] = manager_info.get('manager_name', '')
    target['manager_email'] = manager_info.get('manager_email', '')
    target['manager_phone'] = manager_info.get('manager_phone', '')


def determine_location_based_manager(user_record):
    """Determine manager overrides based on location and department."""
    location = (user_record.get('location') or '').strip().lower()
    department = (user_record.get('department') or '').strip().lower()

    if department == 'industrial relations':
        dept_manager = get_department_manager('Industrial Relations')
        if dept_manager:
            return dept_manager

    if department == 'admin':
        dept_manager = get_department_manager('Admin')
        if dept_manager:
            return dept_manager

    if department == 'project management':
        dept_manager = get_department_manager('Project Management')
        if dept_manager:
            return dept_manager

    if department == 'information technology':
        dept_manager = get_department_manager('Information Technology')
        if dept_manager:
            return dept_manager

    if department in ('security', 'environment health & safety'):
        return {**RAJAN_MANAGER_INFO}

    if department == 'technical service & infrastructure':
        return {**TRIBHUVAN_MANAGER_INFO}

    if location == 'manesar':
        if department in MANESAR_DEPARTMENTS_FOR_MANOJ:
            return {**MANOJ_MANAGER_INFO}
        if department in MANESAR_DEPARTMENTS_FOR_ANKUR:
            return {**ANKUR_MANAGER_INFO}
        if department in MANESAR_DEPARTMENTS_FOR_SHIVAM:
            return {**SHIVAM_MANAGER_INFO}

    if location == 'bawal':
        dept_manager = get_department_manager(user_record.get('department', ''))
        if dept_manager:
            return dept_manager

    return None


def apply_location_based_manager(user_record, display_target=None, log_context=''):
    """Apply location-based manager overrides to the user/session and optional display target."""
    manager_override = determine_location_based_manager(user_record)
    if manager_override:
        set_manager_fields(user_record, manager_override)
        if display_target is not None:
            set_manager_fields(display_target, manager_override)
        if log_context:
            print(
                f"✅ {log_context}: Location-based manager override -> "
                f"{manager_override.get('manager_name', 'N/A')} "
                f"({manager_override.get('manager_email', 'N/A')})"
            )
    return manager_override


# Hardcoded Employees - Not in SAP API but need access to book taxi requests
HARDCODED_EMPLOYEES = {
    '7001009': {
        'emp_code': '7001009',
        'employee_name': 'Yao Demian',
        'dob': '11-11-1986',
        'employee_email': 'YaoDM@nvtpower.com',
        'employee_phone': '9765499226',
        'department': 'Expats',
        'division': ' Expats Div',
        'location': 'NVTI',
        'manager_id': '9022761',
        'manager_name': 'Nitika Arora',
        'manager_email': 'nitika.arora@nvtpower.com',
        'manager_phone': '9765499226'
    },
    '7001021': {
        'emp_code': '7001021',
        'employee_name': 'Yang Kaibin',
        'dob': '27-03-1993',
        'employee_email': 'YangKB@nvtpower.com',
        'employee_phone': '9765499226',
        'department': 'Expats',
        'division': ' Expats Div',
        'location': 'NVTI',
        'manager_id': '9022761',
        'manager_name': 'Nitika Arora',
        'manager_email': 'nitika.arora@nvtpower.com',
        'manager_phone': '9765499226'
    },
    '7001026': {
        'emp_code': '7001026',
        'employee_name': 'Hu Chuangjia',
        'dob': '20-11-1991',
        'employee_email': 'HuCJ2@nvtpower.com',
        'employee_phone': '9765499226',
        'department': 'Expats',
        'division': ' Expats Div',
        'location': 'NVTI',
        'manager_id': '9022761',
        'manager_name': 'Nitika Arora',
        'manager_email': 'nitika.arora@nvtpower.com',
        'manager_phone': '9765499226'
    },
    '7001027': {
        'emp_code': '7001027',
        'employee_name': 'He Jianjun',
        'dob': '24-07-1983',
        'employee_email': 'HeJianJun@nvtpower.com',
        'employee_phone': '9765499226',
        'department': 'Expats',
        'division': ' Expats Div',
        'location': 'NVTI',
        'manager_id': '9022761',
        'manager_name': 'Nitika Arora',
        'manager_email': 'nitika.arora@nvtpower.com',
        'manager_phone': '9765499226'
    },
    '7001030': {
        'emp_code': '7001030',
        'employee_name': 'Su Xin',
        'dob': '09-03-1990',
        'employee_email': 'sux@nvtpower.com',
        'employee_phone': '9765499226',
        'department': 'Expats',
        'division': ' Expats Div',
        'location': 'NVTI',
        'manager_id': '9022761',
        'manager_name': 'Nitika Arora',
        'manager_email': 'nitika.arora@nvtpower.com',
        'manager_phone': '9765499226'
    },
    '7001032': {
        'emp_code': '7001032',
        'employee_name': 'Shi Jiaojiang',
        'dob': '16-10-1988',
        'employee_email': 'ShiJJ@nvtpower.com',
        'employee_phone': '9765499226',
        'department': 'Expats',
        'division': ' Expats Div',
        'location': 'NVTI',
        'manager_id': '9022761',
        'manager_name': 'Nitika Arora',
        'manager_email': 'nitika.arora@nvtpower.com',
        'manager_phone': '9765499226'
    },
    '7001033': {
        'emp_code': '7001033',
        'employee_name': 'Wu Dunfa',
        'dob': '18-07-1985',
        'employee_email': 'WuDF@nvtpower.com',
        'employee_phone': '9765499226',
        'department': 'Expats',
        'division': ' Expats Div',
        'location': 'NVTI',
        'manager_id': '9022761',
        'manager_name': 'Nitika Arora',
        'manager_email': 'nitika.arora@nvtpower.com',
        'manager_phone': '9765499226'
    },
    '7001034': {
        'emp_code': '7001034',
        'employee_name': 'Zhou Huaming',
        'dob': '16-04-1980',
        'employee_email': 'zhouhm@nvtpower.com',
        'employee_phone': '9765499226',
        'department': 'Expats',
        'division': ' Expats Div',
        'location': 'NVTI',
        'manager_id': '9022761',
        'manager_name': 'Nitika Arora',
        'manager_email': 'nitika.arora@nvtpower.com',
        'manager_phone': '9765499226'
    },
    '7001035': {
        'emp_code': '7001035',
        'employee_name': 'Wei Zhongxian',
        'dob': '20-05-1971',
        'employee_email': 'weizx@nvtpower.com',
        'employee_phone': '9765499226',
        'department': 'Expats',
        'division': ' Expats Div',
        'location': 'NVTI',
        'manager_id': '9022761',
        'manager_name': 'Nitika Arora',
        'manager_email': 'nitika.arora@nvtpower.com',
        'manager_phone': '9765499226'
    },
    '7001036': {
        'emp_code': '7001036',
        'employee_name': 'Song GangFan',
        'dob': '10-04-1979',
        'employee_email': 'songgf@nvtpower.com',
        'employee_phone': '9765499226',
        'department': 'Expats',
        'division': ' Expats Div',
        'location': 'NVTI',
        'manager_id': '9022761',
        'manager_name': 'Nitika Arora',
        'manager_email': 'nitika.arora@nvtpower.com',
        'manager_phone': '9765499226'
    },
    '7001037': {
        'emp_code': '7001037',
        'employee_name': 'Fu Yanfei',
        'dob': '01-02-1991',
        'employee_email': 'FuYF@nvtpower.com',
        'employee_phone': '9765499226',
        'department': 'Expats',
        'division': ' Expats Div',
        'location': 'NVTI',
        'manager_id': '9022761',
        'manager_name': 'Nitika Arora',
        'manager_email': 'nitika.arora@nvtpower.com',
        'manager_phone': '9765499226'
    }
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def test_db_connection():
    """Test database connection before starting the app"""
    try:
        print(f"🧪 Testing database connection...")
        conn = db_pool.getconn()
        with conn.cursor() as c:
            c.execute('SELECT version()')
            version = c.fetchone()
            print(f"✅ Database connection test successful")
            print(f"   PostgreSQL version: {version[0]}")
        db_pool.putconn(conn)
        return True
    except Exception as e:
        print(f"❌ Database connection test failed: {str(e)}")
        return False

def check_and_fix_table_structure():
    """Check if taxi_requests table has correct column order and fix if needed"""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            # Check if table exists
            c.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'taxi_requests'
                )
            """)
            table_exists = c.fetchone()[0]

            if not table_exists:
                print("📝 taxi_requests table does not exist - will be created with correct structure")
                return True

            # Get current column order
            c.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'taxi_requests'
                ORDER BY ordinal_position
            """)
            current_columns = [row[0] for row in c.fetchall()]

            # Expected column order
            expected_columns = [
                'id', 'emp_code', 'employee_name', 'employee_email', 'employee_phone',
                'department', 'from_location', 'to_location', 'travel_date', 'travel_time',
                'purpose', 'passengers', 'status', 'manager_email', 'hod_response',
                'hod_approval_date', 'admin_response', 'taxi_details', 'submission_date',
                'admin_response_date', 'created_at', 'assigned_cost', 'type_of_ride',
                'vehicle_company', 'vehicle_type', 'vehicle_number', 'returning_ride',
                'return_from_location', 'return_to_location', 'return_time'
            ]

            if current_columns == expected_columns:
                print("✅ taxi_requests table has correct column order")
                return True
            else:
                print("⚠️ taxi_requests table has incorrect column order - fixing...")

                # Create backup
                backup_table = f"taxi_requests_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                c.execute(f"CREATE TABLE {backup_table} AS SELECT * FROM taxi_requests")
                print(f"✅ Backup created: {backup_table}")

                # Create new table with correct order
                c.execute('''CREATE TABLE taxi_requests_new
                            (id TEXT PRIMARY KEY,                    -- 0
                             emp_code TEXT NOT NULL,                 -- 1
                             employee_name TEXT NOT NULL,            -- 2
                             employee_email TEXT NOT NULL,           -- 3
                             employee_phone TEXT NOT NULL,           -- 4
                             department TEXT,                        -- 5
                             from_location TEXT NOT NULL,            -- 6
                             to_location TEXT NOT NULL,              -- 7
                             travel_date DATE NOT NULL,              -- 8
                             travel_time TIME NOT NULL,              -- 9
                             purpose TEXT NOT NULL,                  -- 10
                             passengers INTEGER DEFAULT 1,           -- 11
                             status TEXT DEFAULT 'Pending Manager Approval', -- 12
                             manager_email TEXT,                     -- 13
                             hod_response TEXT,                      -- 14
                             hod_approval_date TIMESTAMP,            -- 15
                             admin_response TEXT,                    -- 16
                             taxi_details TEXT,                      -- 17
                             submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 18
                             admin_response_date TIMESTAMP,          -- 19
                             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 20
                             assigned_cost DECIMAL(10,2) DEFAULT 0.00, -- 21
                             type_of_ride TEXT DEFAULT 'company_taxi', -- 22
                             vehicle_company TEXT,                   -- 23
                             vehicle_type TEXT,                      -- 24
                             vehicle_number TEXT,                    -- 25
                             returning_ride TEXT DEFAULT 'no',       -- 26
                             return_from_location TEXT,              -- 27
                             return_to_location TEXT,                -- 28
                             return_time TIME)                       -- 29
                             ''')

                # Copy data in correct order
                column_list = ", ".join(expected_columns)
                c.execute(f"""
                    INSERT INTO taxi_requests_new ({column_list})
                    SELECT {column_list} FROM taxi_requests
                """)

                # Replace old table
                c.execute("DROP TABLE taxi_requests")
                c.execute("ALTER TABLE taxi_requests_new RENAME TO taxi_requests")

                conn.commit()
                print("✅ taxi_requests table structure fixed successfully")
                return True

    except Exception as e:
        print(f"❌ Error fixing table structure: {str(e)}")
        conn.rollback()
        return False
    finally:
        db_pool.putconn(conn)

def init_db():
    print(f"🔍 Initializing database...")
    print(f"   Using database: {app.config['DB_CONFIG']['dbname']}")

    try:
        conn = db_pool.getconn()
        print(f"✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        print(f"   Please check your database configuration:")
        print(f"   - Database: {app.config['DB_CONFIG']['dbname']}")
        print(f"   - Host: {app.config['DB_CONFIG']['host']}")
        print(f"   - Port: {app.config['DB_CONFIG']['port']}")
        print(f"   - User: {app.config['DB_CONFIG']['user']}")
        raise

    try:
        # First check and fix table structure if needed
        print("🔍 Checking taxi_requests table structure...")
        check_and_fix_table_structure()

        with conn.cursor() as c:
            # Create taxi_requests table with correct column order (30 columns)
            # This ensures consistent column indexing across different devices
            c.execute('''CREATE TABLE IF NOT EXISTS taxi_requests
                        (id TEXT PRIMARY KEY,                    -- 0
                         emp_code TEXT NOT NULL,                 -- 1
                         employee_name TEXT NOT NULL,            -- 2
                         employee_email TEXT NOT NULL,           -- 3
                         employee_phone TEXT NOT NULL,           -- 4
                         department TEXT,                        -- 5
                         from_location TEXT NOT NULL,            -- 6
                         to_location TEXT NOT NULL,              -- 7
                         travel_date DATE NOT NULL,              -- 8
                         travel_time TIME NOT NULL,              -- 9
                         purpose TEXT NOT NULL,                  -- 10
                         passengers INTEGER DEFAULT 1,           -- 11
                         status TEXT DEFAULT 'Pending Manager Approval', -- 12
                         manager_email TEXT,                     -- 13
                         hod_response TEXT,                      -- 14
                         hod_approval_date TIMESTAMP,            -- 15
                         admin_response TEXT,                    -- 16
                         taxi_details TEXT,                      -- 17
                         submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 18
                         admin_response_date TIMESTAMP,          -- 19
                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 20
                         assigned_cost DECIMAL(10,2) DEFAULT 0.00, -- 21
                         type_of_ride TEXT DEFAULT 'company_taxi', -- 22
                         vehicle_company TEXT,                   -- 23
                         vehicle_type TEXT,                      -- 24
                         vehicle_number TEXT,                    -- 25
                         returning_ride TEXT DEFAULT 'no',       -- 26
                         return_from_location TEXT,              -- 27
                         return_to_location TEXT,                -- 28
                         return_time TIME)                       -- 29
                         ''')

            # Create login_logs table if it doesn't exist
            c.execute('''CREATE TABLE IF NOT EXISTS login_logs
                        (id SERIAL PRIMARY KEY,
                         emp_code TEXT NOT NULL,
                         employee_name TEXT NOT NULL,
                         login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         ip_address TEXT,
                         success BOOLEAN DEFAULT TRUE,
                         error_message TEXT)''')

            # Create HODs table if it doesn't exist
            c.execute('''CREATE TABLE IF NOT EXISTS hods
                        (id SERIAL PRIMARY KEY,
                         emp_code TEXT UNIQUE NOT NULL,
                         hod_name TEXT NOT NULL,
                         hod_email TEXT NOT NULL,
                         hod_phone TEXT NOT NULL,
                         department TEXT NOT NULL,
                         password TEXT NOT NULL DEFAULT 'admin123',
                         is_active BOOLEAN DEFAULT TRUE,
                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            # Create taxi_feedback table if it doesn't exist
            c.execute('''CREATE TABLE IF NOT EXISTS taxi_feedback
                        (id SERIAL PRIMARY KEY,
                         request_id TEXT NOT NULL,
                         emp_code TEXT NOT NULL,
                         employee_name TEXT NOT NULL,
                         employee_email TEXT NOT NULL,
                         rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                         comment TEXT,
                         start_meter DECIMAL(10,2),
                         end_meter DECIMAL(10,2),
                         total_distance DECIMAL(10,2),
                         feedback_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         FOREIGN KEY (request_id) REFERENCES taxi_requests(id) ON DELETE CASCADE)''')

            # Create admins table if it doesn't exist
            c.execute('''CREATE TABLE IF NOT EXISTS admins
                        (id SERIAL PRIMARY KEY,
                         emp_code TEXT UNIQUE NOT NULL,
                         admin_name TEXT NOT NULL,
                         admin_email TEXT NOT NULL,
                         admin_phone TEXT NOT NULL,
                         password TEXT NOT NULL DEFAULT 'admin123',
                         is_active BOOLEAN DEFAULT TRUE,
                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            # Create managers table if it doesn't exist
            c.execute('''CREATE TABLE IF NOT EXISTS managers
                        (id SERIAL PRIMARY KEY,
                         emp_code TEXT UNIQUE NOT NULL,
                         manager_name TEXT NOT NULL,
                         manager_email TEXT NOT NULL,
                         manager_phone TEXT,
                         department TEXT,
                         is_active BOOLEAN DEFAULT TRUE,
                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            # Create budget_management table if it doesn't exist
            c.execute('''CREATE TABLE IF NOT EXISTS budget_management
                        (id SERIAL PRIMARY KEY,
                         total_budget DECIMAL(12,2) DEFAULT 100000.00,
                         used_budget DECIMAL(12,2) DEFAULT 0.00,
                         remaining_budget DECIMAL(12,2) DEFAULT 100000.00,
                         budget_year INTEGER UNIQUE DEFAULT EXTRACT(YEAR FROM CURRENT_DATE),
                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

            # Create taxi_reason table if it doesn't exist
            c.execute('''CREATE TABLE IF NOT EXISTS taxi_reason
                        (id SERIAL PRIMARY KEY,
                         reference_id TEXT NOT NULL,
                         reason TEXT,
                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         FOREIGN KEY (reference_id) REFERENCES taxi_requests(id) ON DELETE CASCADE)''')

            # Create feedback_reminders table to track sent reminders
            c.execute('''CREATE TABLE IF NOT EXISTS feedback_reminders
                        (id SERIAL PRIMARY KEY,
                         request_id TEXT NOT NULL,
                         reminder_type TEXT NOT NULL,
                         sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         UNIQUE(request_id, reminder_type),
                         FOREIGN KEY (request_id) REFERENCES taxi_requests(id) ON DELETE CASCADE)''')

            # Create hod_budget table for individual HOD budget management
            c.execute('''CREATE TABLE IF NOT EXISTS hod_budget
                        (id SERIAL PRIMARY KEY,
                         hod_emp_code TEXT NOT NULL,
                         hod_name TEXT NOT NULL,
                         hod_email TEXT NOT NULL,
                         total_budget DECIMAL(12,2) DEFAULT 50000.00,
                         used_budget DECIMAL(12,2) DEFAULT 0.00,
                         remaining_budget DECIMAL(12,2) DEFAULT 50000.00,
                         budget_year INTEGER DEFAULT EXTRACT(YEAR FROM CURRENT_DATE),
                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         UNIQUE(hod_emp_code, budget_year))''')

            # Insert HOD (only 9025857)
            hods_data = [
                ('9025857', 'Piyush Tiwari', 'piyush.tiwari@nvtpower.com', '6395747398', 'Center of Excellence')
            ]

            for hod in hods_data:
                c.execute('''INSERT INTO hods (emp_code, hod_name, hod_email, hod_phone, department)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (emp_code) DO UPDATE SET
                            hod_name = EXCLUDED.hod_name,
                            hod_email = EXCLUDED.hod_email,
                            hod_phone = EXCLUDED.hod_phone,
                            department = EXCLUDED.department''', hod)

            # Insert admins (9025857 as both HOD and Admin, 9022761 as Admin)
            admins_data = [
                ('9025857', 'Piyush Tiwari', 'piyush.tiwari@nvtpower.com', '6395747398', 'admin123'),
                ('9022761', 'Nitika Arora', 'nitika.arora@nvtpower.com', '9765499226', 'admin123')
            ]

            for admin in admins_data:
                c.execute('''INSERT INTO admins (emp_code, admin_name, admin_email, admin_phone, password)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (emp_code) DO UPDATE SET
                            admin_name = EXCLUDED.admin_name,
                            admin_email = EXCLUDED.admin_email,
                            admin_phone = EXCLUDED.admin_phone''', admin)

            # Insert initial budget data if not exists
            current_year = datetime.now().year
            c.execute('SELECT COUNT(*) FROM budget_management WHERE budget_year = %s', (current_year,))
            budget_exists = c.fetchone()[0] > 0

            if not budget_exists:
                c.execute('''INSERT INTO budget_management (total_budget, used_budget, remaining_budget, budget_year)
                            VALUES (100000.00, 0.00, 100000.00, %s)''', (current_year,))

            # Insert initial HOD budget data for department managers
            hod_budget_data = [
                # Managers found in initial hod_budget_data
                ('9025802', 'Shivam Chaturvedi', 'shivam.chaturvedi@nvtpower.com', 50000.00, 0.00, 50000.00),
                ('9013753', 'Sudarshan Kumar', 'sudarshan.kumar@nvtpower.com', 50000.00, 0.00, 50000.00),
                ('9017113', 'Tribhuvan Agnihotri', 'tribhuvan.agnihotri@nvtpower.com', 50000.00, 0.00, 50000.00),
                ('9023422', 'Mohit Agarwal', 'mohit.agarwal@nvtpower.com', 50000.00, 0.00, 50000.00),
                ('9022761', 'Nitika Arora', 'nitika.arora@nvtpower.com', 50000.00, 0.00, 50000.00),
                ('9025421', 'Rajan Vashisht', 'rajan.vashisht@nvtpower.com', 50000.00, 0.00, 50000.00),
                ('9023649', 'Jayesh Sinha', 'jayesh.sinha@nvtpower.com', 50000.00, 0.00, 50000.00),
                ('9012706', 'Manoj Saini', 'manoj.saini@nvtpower.com', 50000.00, 0.00, 50000.00),

                # Managers missing in initial hod_budget_data but in DEPARTMENT_MANAGER_MAPPING
                ('9024436', 'Ankur Tandon', 'ankur.tandon@nvtpower.com', 50000.00, 0.00, 50000.00),
                ('9024982', 'V G Padmanabhan', 'vg.padmanabhan@nvtpower.com', 50000.00, 0.00, 50000.00),
                ('9023418', 'Nishant Sharma', 'nishant.sharma@nvtpower.com', 50000.00, 0.00, 50000.00),
                ('9024785', 'Vinod Kumar', 'vinod.kumar@nvtpower.com', 50000.00, 0.00, 50000.00),
                (' 9022826', 'Pawan Tyagi', 'pawan.tyagi@nvtpower.com', 50000.00, 0.00, 50000.00),
            ]

            for hod_budget in hod_budget_data:
                c.execute('''INSERT INTO hod_budget (hod_emp_code, hod_name, hod_email, total_budget, used_budget, remaining_budget, budget_year)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (hod_emp_code, budget_year) DO UPDATE SET
                            hod_name = EXCLUDED.hod_name,
                            hod_email = EXCLUDED.hod_email''',
                            (hod_budget[0], hod_budget[1], hod_budget[2], hod_budget[3], hod_budget[4], hod_budget[5], current_year))

            # Create indexes
            c.execute('CREATE INDEX IF NOT EXISTS idx_taxi_emp_code ON taxi_requests(emp_code)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_taxi_status ON taxi_requests(status)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_login_emp_code ON login_logs(emp_code)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_hod_emp_code ON hods(emp_code)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_budget_management_year ON budget_management(budget_year)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_feedback_reminders_request_id ON feedback_reminders(request_id)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_feedback_reminders_type ON feedback_reminders(reminder_type)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_hod_budget_emp_code ON hod_budget(hod_emp_code)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_hod_budget_year ON hod_budget(budget_year)')

        conn.commit()
        print("✅ Database initialized successfully with HOD functionality")
        print("✅ HOD Budget table created with individual budget tracking for 14 department managers")
    except Exception as e:
        print(f"❌ Database initialization error: {str(e)}")
        raise
    finally:
        db_pool.putconn(conn)

# HOD Email Mapping - Maps HOD employee codes to their correct @nvtpower.com emails
HOD_EMAIL_MAPPING = {
    '9017113': 'tribhuvan.agnihotri@nvtpower.com',  # Tribhuvan Agnihotri
    '9025023': 'sandeep.kumar@nvtpower.com',  # Sandeep Kumar
    '9025853': 'nitin@nvtpower.com',  # Nitin
    '9025881': 'ajay.vyas@nvtpower.com',  # Ajay Vyas
    '9025851': 'akshay.yadav@nvtpower.com',  # Akshay Kumar Yadav
    '9025540': 'kapil.kumar@nvtpower.com',  # Kapil Kumar
    '9018847': 'sandeep.kumar2@nvtpower.com',  # Sandeep Kumar
    '9024443': 'agam.singh@nvtpower.com',  # Agam Singh
    '9023649': 'jayesh.sinha@nvtpower.com',  # Jayesh Sinha
    '9016864': 'shirish.prasad@nvtpower.com',  # Shirish Prasad
    '9025802': 'shivam.chaturvedi@nvtpower.com',  # Shivam Chaturvedi
    '9025812': 'mahendra.raj@nvtpower.com',  # Mahendra Raj
    '9025210': 'rohan.goswami@nvtpower.com',  # Rohan Goswami
    '9025421': 'rajan.vashisht@nvtpower.com',  # Rajan Vashisht
    '9023638': 'dinesh.rathor@nvtpower.com',  # Dinesh Kumar Rathor
    '9025537': 'shubham.mall@nvtpower.com',  # Shubham Mall
    '9024785': 'vinod.kumar@nvtpower.com',  # Vinod Kumar
    '9025488': 'pawan.singh@nvtpower.com',  # Pawan Singh
    '9025137': 'i.shankar@nvtpower.com',  # Irulamuthu Shankar
    '9012834': 'rajesh.kumar@nvtpower.com',  # Rajesh Kumar
    '9025301': 'manish.yadav@nvtpower.com',  # Manish Kumar
    '9020328': 'pradeep.kumar@nvtpower.com',  # Pradeep Kumar
    '9022246': 'sunil.kumar@nvtpower.com',  # Sunil Kumar
    '9023636': 'abhishek.gupta@nvtpower.com',  # Abhishek Gupta
    '9024874': 'mohit.verma@nvtpower.com',  # Mohit Verma
    '9025891': 'deepak.singh@nvtpower.com',  # Deepak Singh
    '9025724': 'gourav.gupta@nvtpower.com',  # Gourav Gupta
    '9017113': 'tribhuvan.agnihotri@nvtpower.com',  # Tribhuvan Agnihotri
    '9023652': 'kamal.saini@nvtpower.com',  # Kamal Kant Saini
    '9023418': 'nishant.sharma@nvtpower.com',  # Nishant Sharma
}

# Manager Email Mapping - Maps manager IDs to their correct @nvtpower.com emails
MANAGER_EMAIL_MAPPING = {
    '9022761': 'nitika.arora@nvtpower.com',  # Nitika Arora
    '9025802': 'Shivam.Chaturvedi@nvtpower.com',  # Shivam Chaturvedi
    '9025812': 'Mahendra.Raj@nvtpower.com',  # Mahendra Raj
    '9024443': 'agam.singh@nvtpower.com',  # Agam Singh
    '9016864': 'shirish.Prasad@nvtpower.com',  # Shirish Prasad
    '9023649': 'jayesh.sinha@nvtpower.com',  # Jayesh Sinha
    '9025210': 'rohan.goswami@nvtpower.com',  # Rohan Goswami
    '9025421': 'rajan.vashisht@nvtpower.com',  # Rajan Vashisht
    '9023638': 'dinesh.rathor@nvtpower.com',  # Dinesh Kumar Rathor
    '9025537': 'shubham.mall@nvtpower.com',  # Shubham Mall
    '9024785': 'vinod.kumar@nvtpower.com',  # Vinod Kumar
    '9025488': 'pawan.singh@nvtpower.com',  # Pawan Singh
    '9025137': 'i.shankar@nvtpower.com',  # Irulamuthu Shankar
    '9012834': 'rajesh.kumar@nvtpower.com',  # Rajesh Kumar
    '9025301': 'manish.yadav@nvtpower.com',  # Manish Kumar
    '9020328': 'pradeep.kumar@nvtpower.com',  # Pradeep Kumar
    '9017113': 'tribhuvan.agnihotri@nvtpower.com',  # Tribhuvan Agnihotri
    '9022246': 'sunil.kumar@nvtpower.com',  # Sunil Kumar
    '9023636': 'abhishek.gupta@nvtpower.com',  # Abhishek Gupta
    '9023418': 'nishant.sharma@nvtpower.com',  # Nishant Sharma
    '9025199': 'Amerjeet.singh@nvtpower.com',  # Amerjeet Singh
    '9012706': 'manoj.saini@nvtpower.com',  # Manoj Saini
    '9022611': 'nirdosh.khosia@nvtpower.com',  # Nirdosh Khosia
    '9025755': 'Saurav.Bhardwaj@nvtpower.com',  # Saurav Bhardwaj
    '9025633': 'lalit.sharma@nvtpower.com',  # Lalit Sharma
    '9025054': 'pawan.kumar@nvtpower.com',  # Pawan Kumar
    '9025721': 'Abhishek.Singh@nvtpower.com',  # Abhishek Kumar Singh
    '9023188': 'krishna.sharma@nvtpower.com',  # Krishna Kumar Sharma
    '9025015': 'Jagdish.Rawat@nvtpower.com',  # Jagdish Rawat
    '9013753': 'sudarshan.kumar@nvtpower.com',  # Sudarshan Kumar
    '9022826': 'pawan.tyagi@nvtpower.com',  # Pawan Kumar Tyagi
    '9017944': 'satyendra.prasad@nvtpower.com',  # Satyendra Prasad
    '9024879': 'manoj.sharma@nvtpower.com',  # Manoj Sharma
    '9025254': 'rahul.tyagi@nvtpower.com',  # Rahul Tyagi
    '9021930': 'brijesh.rao@nvtpower.com',  # Brijesh Rao
    '9023579': 'pankaj.jha@nvtpower.com',  # Pankaj Kumar Jha
    '9023655': 'vipin.soni@nvtpower.com',  # Vipin Soni
    '9025426': 'yogender.yadav@nvtpower.com',  # Yogender Yadav
    '9025381': 'munish.kumar@nvtpower.com',  # Munish Kumar
    '9025320': 'sunil.goyal@nvtpower.com',  # Sunil
    '9024581': 'sunny.arora@nvtpower.com',  # Sunny Arora
    '9024660': 'anil.gupta@nvtpower.com',  # Anil Kumar Gupta
    '9025160': 'Dinesh.Kumar1@nvtpower.com',  # Dinesh Kumar
    '9014629': 'rajiv.dinodia@nvtpower.com',  # Rajiv Kumar
    '9024436': 'ankur.tandon@nvtpower.com',  # Ankur Tandon
    '9023422': 'mohit.agarwal@nvtpower.com',  # Mohit Agarwal
    '9025398': 'Saveen.Bhutani@nvtpower.com',  # Saveen Bhutani
    '9022958': 'arun.saini@nvtpower.com',  # Arun
    '9025351': 'mohit.sharma@nvtpower.com',  # Mohit Sharma
    '9025230': 'amit.kumar3@nvtpower.com',  # Amit Kumar
    '9024005': 'satish.kumar@nvtpower.com',  # Satish Kumar
    '9022169': 'shashwat.verma@nvtpower.com',  # Shashwat Verma
    '9020339': 'ganesh.kumar@nvtpower.com',  # Ganesh Kumar
    '9025253': 'Rajesh.kumar2@nvtpower.com',  # Rajesh Kumar
    '9024772': 'himanshu.varshney@nvtpower.com',  # Himanshu Varshney
    '9023635': 'anil.kumar@nvtpower.com',  # Anil Kumar
    '9024863': 'sanchit.mehta@nvtpower.com',  # Sanchit Mehta
    '9024845': 'rahul.mishra@nvtpower.com',  # Rahul Mishra
    '9025049': 'Sakshi.Goswani@nvtpower.com',  # Sakshi Goswami
    '9023642': 'rishi.baghel@nvtpower.com',  # Rishi Kumar Baghel
    '9024874': 'mohit.verma@nvtpower.com',  # Mohit Verma
    '9025891': 'deepak.singh@nvtpower.com',  # Deepak Singh
    '9025724': 'gourav.gupta@nvtpower.com',  # Gourav Gupta
    '9017113': 'tribhuvan.agnihotri@nvtpower.com',  # Tribhuvan Agnihotri
    '9023652': 'kamal.saini@nvtpower.com',  # Kamal Kant Saini
    '9023607': 'prince.kumar@nvtpower.com',  # Prince Kumar
    '9022713': 'deepakkumar.yadav@nvtpower.com',  # Deepak Yadav
    '9024919': 'dinesh.chaudhary@nvtpower.com',  # Dinesh Kumar Chaudhary
    '9023352': 'deep.upadhyay@nvtpower.com',  # Deep Kumar Upadhyay
    '9023631': 'Parmjeet.Singh@nvtpower.com',  # Parmjeet Singh
    '9023647': 'devraj.kaushik@nvtpower.com',  # Devraj Kaushik
    '9024789': 'naveen.n@nvtpower.com',  # Naveen
    '9020234': 'Kuldeep.Kumar@nvtpower.com',  # Kuldeep Kumar
    '9023610': 'Manpreet.singh@nvtpower.com',  # Manpreet Singh
    '9025140': 'rahul.verma@nvtpower.com',  # Rahul Verma
    '9024851': 'amit.kumar@nvtpower.com',  # Amit Kumar
    '9024948': 'sunil.bisht@nvtpower.com',  # Sunil Bisht
    '9016895': 'manoj.singh@nvtpower.com',  # Manoj Singh
    '9025019': 'bhushan.kumar@nvtpower.com',  # Bhushan Kumar
    '9021279': 'ankit.asrani@nvtpower.com',  # Ankit Asrani
    '9016946': 'ashok.kumar@nvtpower.com',  # Ashok Kumar
    '9024011': 'naveen.singh@nvtpower.com',  # Naveen Singh
    '9020370': 'Mandeep.redhu@nvtpower.com',  # Mandeep Redhu
    '9016959': 'sandeep.rao@nvtpower.com',  # Sandeep Kumar
    '9022708': 'ravinder.ahri@nvtpower.com',  # Ravinder Kumar
    '9024695': 'paridhi.tiwari@nvtpower.com',  # Paridhi Tiwari
    '9025332': 'vaibhav.pandey@nvtpower.com',  # Vaibhav Pandey
    '9024438': 'navdeep.yadav@nvtpower.com',  # Navdeep Yadav
    '9019676': 'rakesh.pathania@nvtpower.com',  # Rakesh Kumar Pathania
    '9025033': 'Manjeet.Kumar@nvtpower.com',  # Manjeet Kumar
    '9024982': 'vg.padmanabhan@nvtpower.com',  # V G Padmanabhan
}

# HOD Access Mapping - Maps employee codes to HOD dashboard access
# RESTRICTED: Only these specific HOD employee codes have access to HOD dashboard
HOD_ACCESS_CODES = {
    '9024982': {  # V G Padmanabhan - Warranty
        'name': 'V G Padmanabhan',
        'department': 'Warranty',
        'access_level': 'full'
    },
    '9025857': {  # Authorized HOD
        'name': 'Authorized HOD',
        'department': 'Management',
        'access_level': 'full'
    },
    '9024436': {  # Ankur Tandon - Finance & Accounts, Central Warehouse and Store, Production Planning & Control
        'name': 'Ankur Tandon',
        'department': 'Finance & Accounts',
        'access_level': 'full'
    },
    '9017113': {  # Tribhuvan Agnihotri - Production
        'name': 'Tribhuvan Agnihotri',
        'department': 'Production',
        'access_level': 'full'
    },
    '9013753': {  # Sudarshan Kumar - Maintenance & Engineering
        'name': 'Sudarshan Kumar',
        'department': 'Maintenance & Engineering',
        'access_level': 'full'
    },
    '9025802': {  # Shivam Chaturvedi
        'name': 'Shivam Chaturvedi',
        'department': 'Operations',
        'access_level': 'full'
    },
    '9023422': {  # Mohit Agarwal - Special manager for specific employees
        'name': 'Mohit Agarwal',
        'department': 'Management',
        'access_level': 'full'
    },
    '9022761': {  # Nitika Arora - Admin
        'name': 'Nitika Arora',
        'department': 'Admin',
        'access_level': 'full'
    },
    '9012706': {  # Manoj Saini - Quality (Manesar)
        'name': 'Manoj Saini',
        'department': 'Quality',
        'access_level': 'full'
    },
    '9023549': {  # Authorized HOD
        'name': 'Authorized HOD',
        'department': 'Management',
        'access_level': 'full'
    },
    '9025421': {  # Rajan Vashisht
        'name': 'Rajan Vashisht',
        'department': 'Operations',
        'access_level': 'full'
    },
    '9023418': {  # Nishant Sharma - Project Management
        'name': 'Nishant Sharma',
        'department': 'Project Management',
        'access_level': 'full'
    },
    '9022826': {  # Pawan Kumar Tyagi
        'name': 'Pawan Kumar Tyagi',
        'department': 'Operations',
        'access_level': 'full'
    },
    '9024785': {  # Vinod Kumar
        'name': 'Vinod Kumar',
        'department': 'Operations',
        'access_level': 'full'
    },
    '9023649': {  # Jayesh Sinha
        'name': 'Jayesh Sinha',
        'department': 'Customer Service',
        'access_level': 'full'
    }
}

def fetch_hod_dob_from_sap(emp_code):
    """Fetch HOD date of birth from SAP API for authentication"""
    try:
        # Use the same API endpoint as verify_sap_credentials
        url = f"{SAP_CONFIG['base_url']}EmpJob?$select=division,divisionNav/name,location,locationNav/name,seqNumber,startDate,userId,employmentNav/personNav/personalInfoNav/firstName,employmentNav/personNav/personalInfoNav/middleName,employmentNav/personNav/personalInfoNav/lastName,employmentNav/personNav/personalInfoNav/customString5,payGradeNav/name,customString10Nav/externalName,department,departmentNav/name,employmentNav/empJobRelationshipNav/relationshipTypeNav/externalCode,employmentNav/empJobRelationshipNav/relUserId,employmentNav/empJobRelationshipNav/relUserNav/defaultFullName,employmentNav/personNav/emailNav/emailAddress,employmentNav/personNav/emailNav/isPrimary,employmentNav/personNav/emailNav/emailTypeNav/picklistLabels/label,employmentNav/personNav/countryOfBirth,employmentNav/personNav/phoneNav/phoneNumber,employmentNav/personNav/phoneNav/phoneTypeNav/picklistLabels/label,employmentNav/personNav/personalInfoNav/gender,employmentNav/personNav/personalInfoNav/maritalStatusNav/picklistLabels/label,employmentNav/personNav/dateOfBirth,employmentNav/startDate,employmentNav/customString18,emplStatusNav/picklistLabels/label,employmentNav/personNav/homeAddressNavDEFLT/addressType,employmentNav/personNav/homeAddressNavDEFLT/address1,employmentNav/personNav/homeAddressNavDEFLT/address10,employmentNav/personNav/homeAddressNavDEFLT/address12,employmentNav/personNav/homeAddressNavDEFLT/address14,employmentNav/personNav/homeAddressNavDEFLT/stateNav/picklistLabels/label,employmentNav/personNav/homeAddressNavDEFLT/countyNav/picklistLabels/label,employmentNav/personNav/homeAddressNavDEFLT/cityNav/picklistLabels/label,managerId,managerUserNav/defaultFullName,employmentNav/personNav/personalInfoNav/customString10,employmentNav/personNav/personalInfoNav/customString11,employmentNav/personNav/personalInfoNav/customString8,employmentNav/personNav/personalInfoNav/customString9,customString6,employmentType,customString6Nav/id,customString6Nav/externalCode,customString6Nav/localeLabel,employmentTypeNav/id,employmentTypeNav/externalCode,employmentTypeNav/localeLabel,employmentNav/endDate,employmentNav/customDate6,eventReasonNav/externalCode,eventReasonNav/name&$expand=employmentNav/personNav/personalInfoNav,divisionNav,locationNav,payGradeNav,customString10Nav,departmentNav,employmentNav/empJobRelationshipNav/relationshipTypeNav,employmentNav/empJobRelationshipNav/relUserNav,employmentNav/personNav/emailNav/emailTypeNav/picklistLabels,employmentNav/personNav/phoneNav/phoneTypeNav/picklistLabels,employmentNav/personNav/personalInfoNav/maritalStatusNav/picklistLabels,emplStatusNav/picklistLabels,employmentNav/personNav/homeAddressNavDEFLT/stateNav/picklistLabels,employmentNav/personNav/homeAddressNavDEFLT/countyNav/picklistLabels,employmentNav/personNav/homeAddressNavDEFLT/cityNav/picklistLabels,managerUserNav,customString6Nav,employmentTypeNav,eventReasonNav&$filter=userId eq '{emp_code}'&$format=json&$orderby=employmentNav/startDate"

        response = requests.get(
            url,
            auth=HTTPBasicAuth(SAP_CONFIG['username'], SAP_CONFIG['password']),
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get('d', {}).get('results', [])

            if results:
                employee_data = results[0]

                # Get date of birth from personNav
                sap_dob = employee_data.get('employmentNav', {}).get('personNav', {}).get('dateOfBirth', '')

                # Convert SAP date format to DDMMYYYY format
                sap_dob_formatted = None
                if sap_dob:
                    try:
                        sap_dob_str = str(sap_dob)

                        if sap_dob_str.startswith('/Date(') and sap_dob_str.endswith(')/'):
                            # Extract milliseconds from "/Date(milliseconds)/"
                            milliseconds = int(sap_dob_str[6:-2])
                        elif sap_dob_str.isdigit():
                            # Direct milliseconds
                            milliseconds = int(sap_dob_str)
                        else:
                            milliseconds = None

                        if milliseconds:
                            # Convert milliseconds to date
                            from datetime import datetime
                            date_obj = datetime.fromtimestamp(milliseconds / 1000)
                            sap_dob_formatted = date_obj.strftime('%d%m%Y')
                        else:
                            # Try YYYY-MM-DD format
                            if '-' in sap_dob_str:
                                date_parts = sap_dob_str.split('-')
                                if len(date_parts) == 3:
                                    year, month, day = date_parts
                                    sap_dob_formatted = f"{day.zfill(2)}{month.zfill(2)}{year}"
                            else:
                                # If it's already in DDMMYYYY format
                                sap_dob_formatted = sap_dob_str
                    except Exception as e:
                        print(f"Date conversion error for HOD {emp_code}: {e}")
                        sap_dob_formatted = None

                return {
                    'success': True,
                    'dob': sap_dob_formatted,
                    'employee_data': employee_data
                }

        return {'success': False, 'error': 'HOD not found in SAP'}

    except Exception as e:
        print(f"Error fetching HOD DOB for {emp_code}: {str(e)}")
        return {'success': False, 'error': str(e)}

def is_hod_authorized(emp_code):
    """Check if employee code is authorized for HOD dashboard access - RESTRICTED ACCESS"""
    # SECURITY: Only check hardcoded HOD access codes - database check disabled for security
    # Only the specific HOD employee codes in HOD_ACCESS_CODES can access HOD dashboard
    if emp_code in HOD_ACCESS_CODES:
        return True, HOD_ACCESS_CODES[emp_code]

    # Access denied for all other employee codes, even if they exist in database
    return False, None

def normalize_email_for_matching(email):
    """Normalize email for consistent matching (lowercase, trim whitespace)"""
    if not email:
        return ''
    return email.lower().strip()

def find_matching_requests_for_hod(hod_email, cursor):
    """Find requests that match the HOD email with flexible matching"""
    if not hod_email:
        return []

    normalized_hod_email = normalize_email_for_matching(hod_email)

    # Try exact match first
    cursor.execute('''SELECT id, emp_code, employee_name, manager_email, status
                     FROM taxi_requests
                     WHERE LOWER(TRIM(manager_email)) = %s''', (normalized_hod_email,))
    exact_matches = cursor.fetchall()

    if exact_matches:
        print(f"✅ Found {len(exact_matches)} exact matches for HOD email: {hod_email}")
        return exact_matches

    # Try case-insensitive match
    cursor.execute('''SELECT id, emp_code, employee_name, manager_email, status
                     FROM taxi_requests
                     WHERE LOWER(manager_email) = %s''', (normalized_hod_email,))
    case_insensitive_matches = cursor.fetchall()

    if case_insensitive_matches:
        print(f"✅ Found {len(case_insensitive_matches)} case-insensitive matches for HOD email: {hod_email}")
        return case_insensitive_matches

    # Try partial match (in case there are extra spaces or characters)
    cursor.execute('''SELECT id, emp_code, employee_name, manager_email, status
                     FROM taxi_requests
                     WHERE LOWER(TRIM(manager_email)) LIKE %s''', (f'%{normalized_hod_email}%',))
    partial_matches = cursor.fetchall()

    if partial_matches:
        print(f"✅ Found {len(partial_matches)} partial matches for HOD email: {hod_email}")
        return partial_matches

    print(f"❌ No matches found for HOD email: {hod_email}")
    return []

def get_correct_hod_email(emp_code, sap_email):
    """Get the correct @nvtpower.com email for HOD, using mapping if SAP returns different domain"""
    try:
        # First check if we have a mapping for this HOD
        if str(emp_code) in HOD_EMAIL_MAPPING:
            mapped_email = HOD_EMAIL_MAPPING[str(emp_code)]
            print(f"🔄 Found HOD email mapping, using correct @nvtpower.com email: {mapped_email}")
            return mapped_email

        # If SAP email is already @nvtpower.com, use it
        if sap_email and '@nvtpower.com' in sap_email:
            print(f"✅ SAP email is already @nvtpower.com: {sap_email}")
            return sap_email

        # If SAP email has different domain, try to construct @nvtpower.com email
        if sap_email and '@' in sap_email:
            # Extract the local part (before @)
            local_part = sap_email.split('@')[0]
            constructed_email = f"{local_part}@nvtpower.com"
            print(f"🔄 Constructed @nvtpower.com email from SAP email: {constructed_email}")
            return constructed_email

        # Fallback: return the SAP email as is
        print(f"⚠️ No mapping found, using SAP email as is: {sap_email}")
        return sap_email

    except Exception as e:
        print(f"❌ Error in get_correct_hod_email: {str(e)}")
        return sap_email

def fetch_manager_contact_from_sap(manager_id):
    """Fetch manager email and phone from SAP with caching and lightweight endpoints."""
    if not manager_id:
        return {'manager_email': '', 'manager_phone': ''}

    manager_id_str = str(manager_id).strip()
    if not manager_id_str:
        return {'manager_email': '', 'manager_phone': ''}

    cached = _get_cached_value('manager_contact', manager_id_str)
    if cached:
        return cached

    manager_email = ''
    manager_phone = ''

    # ------------------------------------------------------------------
    # Email lookup (prefer @nvtpower.com, then primary, then first entry)
    # ------------------------------------------------------------------
    try:
        email_url = (
            f"{SAP_CONFIG['base_url']}PerEmail"
            f"?$select=emailAddress,isPrimary,emailType"
            f"&$expand=emailTypeNav/picklistLabels"
            f"&$filter=personIdExternal eq '{manager_id_str}'"
            f"&$format=json"
        )
        response = requests.get(
            email_url,
            auth=HTTPBasicAuth(SAP_CONFIG['username'], SAP_CONFIG['password']),
            timeout=8
        )

        if response.status_code == 200:
            data = response.json()
            email_results = data.get('d', {}).get('results', [])

            preferred_email = None
            primary_email = None
            first_email = None

            for idx, email_record in enumerate(email_results):
                email_addr = email_record.get('emailAddress', '') or ''
                email_addr = email_addr.strip()
                if not first_email and email_addr:
                    first_email = email_addr

                if '@nvtpower.com' in email_addr.lower():
                    preferred_email = email_addr
                    break

                if not primary_email and email_record.get('isPrimary'):
                    primary_email = email_addr

            manager_email = preferred_email or primary_email or first_email or ''

        else:
            print(f"❌ Manager email API failed for {manager_id_str} with status {response.status_code}")

    except Exception as e:
        print(f"❌ Error fetching manager email for {manager_id_str}: {e}")

    if not manager_email and str(manager_id_str) in MANAGER_EMAIL_MAPPING:
        mapped_email = MANAGER_EMAIL_MAPPING[str(manager_id_str)]
        print(f"🔄 Using mapped email as fallback for manager {manager_id_str}: {mapped_email}")
        manager_email = mapped_email

    # ------------------------------------------------------------------
    # Phone lookup (prefer labels containing mobile/cell/whatsapp)
    # ------------------------------------------------------------------
    try:
        phone_url = (
            f"{SAP_CONFIG['base_url']}PerPhone"
            f"?$select=phoneNumber,phoneType"
            f"&$expand=phoneTypeNav/picklistLabels"
            f"&$filter=personIdExternal eq '{manager_id_str}'"
            f"&$format=json"
        )
        response = requests.get(
            phone_url,
            auth=HTTPBasicAuth(SAP_CONFIG['username'], SAP_CONFIG['password']),
            timeout=8
        )

        if response.status_code == 200:
            data = response.json()
            phone_results = data.get('d', {}).get('results', [])

            def picklist_labels(record):
                labels = record.get('phoneTypeNav', {}).get('picklistLabels', {}).get('results', [])
                return [label.get('label', '').lower() for label in labels]

            prioritized = None
            fallback_phone = None
            label_keywords = ['mobile', 'cell', 'whatsapp']

            for record in phone_results:
                number = record.get('phoneNumber', '') or ''
                if not number:
                    continue

                labels = picklist_labels(record)
                lower_number = ''.join(filter(str.isdigit, number))

                if not fallback_phone and lower_number:
                    fallback_phone = number

                if any(keyword in label for label in labels for keyword in label_keywords):
                    prioritized = number
                    break

            raw_phone = prioritized or fallback_phone or ''
            if raw_phone:
                digits_only = ''.join(filter(str.isdigit, raw_phone))
                if digits_only.startswith('91') and len(digits_only) == 12:
                    manager_phone = f"+{digits_only}"
                elif len(digits_only) == 10:
                    manager_phone = f"+91{digits_only}"
                elif raw_phone.startswith('+'):
                    manager_phone = raw_phone
                elif digits_only:
                    manager_phone = f"+{digits_only}"
                else:
                    manager_phone = ''

        else:
            print(f"❌ Manager phone API failed for {manager_id_str} with status {response.status_code}")

    except Exception as e:
        print(f"❌ Error fetching manager phone for {manager_id_str}: {e}")

    contact_payload = {
        'manager_email': manager_email or '',
        'manager_phone': manager_phone or ''
    }
    _set_cached_value('manager_contact', manager_id_str, contact_payload)
    return contact_payload


def fetch_manager_email_from_sap(manager_id):
    """Compatibility wrapper returning only email."""
    return fetch_manager_contact_from_sap(manager_id).get('manager_email', '')


def fetch_manager_phone_from_sap(manager_id):
    """Compatibility wrapper returning only phone."""
    return fetch_manager_contact_from_sap(manager_id).get('manager_phone', '')

def verify_sap_credentials(emp_code, dob):
    """Verify employee credentials using SAP API with employee code and date of birth (DDMMYYYY format)"""

    try:
        # Use trimmed EmpJob endpoint
        url = build_empjob_url(emp_code)

        response = requests.get(
            url,
            auth=HTTPBasicAuth(SAP_CONFIG['username'], SAP_CONFIG['password']),
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get('d', {}).get('results', [])

            print(f"🔍 API Response status: {response.status_code}")
            print(f"🔍 Number of results: {len(results)}")

            if results:
                employee_data = results[0]
                print(f"🔍 Employee data received from SAP API")

                # Extract employee details from the correct path
                personal_info_nav = employee_data.get('employmentNav', {}).get('personNav', {}).get('personalInfoNav', {})

                # Handle both cases: direct object or results array
                first_name = ''
                middle_name = ''
                last_name = ''

                # Check if personalInfoNav is a direct object with firstName
                if isinstance(personal_info_nav, dict) and 'firstName' in personal_info_nav:
                    first_name = personal_info_nav.get('firstName', '')
                    middle_name = personal_info_nav.get('middleName', '')
                    last_name = personal_info_nav.get('lastName', '')
                    print(f"🔍 Name extracted from direct personalInfoNav object")
                # Check if personalInfoNav has a results array
                elif isinstance(personal_info_nav, dict) and 'results' in personal_info_nav:
                    results = personal_info_nav.get('results', [])
                    if results and len(results) > 0:
                        first_name = results[0].get('firstName', '')
                        middle_name = results[0].get('middleName', '')
                        last_name = results[0].get('lastName', '')
                        print(f"🔍 Name extracted from personalInfoNav results array")
                else:
                    print(f"⚠️ Unable to extract name from personalInfoNav structure: {type(personal_info_nav)}")

                print(f"🔍 Name extraction:")
                print(f"   First Name: {first_name}")
                print(f"   Middle Name: {middle_name}")
                print(f"   Last Name: {last_name}")

                sap_dob = ''

                # Get date of birth from personNav directly
                sap_dob = employee_data.get('employmentNav', {}).get('personNav', {}).get('dateOfBirth', '')

                # Convert SAP date format to DDMMYYYY format for comparison
                sap_dob_formatted = None
                if sap_dob:
                    try:
                        # SAP date format is "/Date(milliseconds)/" or just milliseconds
                        sap_dob_str = str(sap_dob)

                        if sap_dob_str.startswith('/Date(') and sap_dob_str.endswith(')/'):
                            # Extract milliseconds from "/Date(milliseconds)/"
                            milliseconds = int(sap_dob_str[6:-2])
                        elif sap_dob_str.isdigit():
                            # Direct milliseconds
                            milliseconds = int(sap_dob_str)
                        else:
                            # Try other formats
                            milliseconds = None

                        if milliseconds:
                            # Convert milliseconds to date
                            from datetime import datetime
                            date_obj = datetime.fromtimestamp(milliseconds / 1000)
                            sap_dob_formatted = date_obj.strftime('%d%m%Y')
                        else:
                            # Try YYYY-MM-DD format
                            if '-' in sap_dob_str:
                                date_parts = sap_dob_str.split('-')
                                if len(date_parts) == 3:
                                    year, month, day = date_parts
                                    sap_dob_formatted = f"{day.zfill(2)}{month.zfill(2)}{year}"
                            else:
                                # If it's already in DDMMYYYY format
                                sap_dob_formatted = sap_dob_str
                    except Exception as e:
                        print(f"Date conversion error: {e}")
                        sap_dob_formatted = None

                # Get phone number from the correct path with enhanced extraction logic
                print(f"🔍 PHONE EXTRACTION (STRICT MODE):")
                phone_nav = employee_data.get('employmentNav', {}).get('personNav', {}).get('phoneNav', {})
                print(f"  Raw phone data: {phone_nav}")

                phone_number = ""
                phone_results = None

                if isinstance(phone_nav, dict) and 'results' in phone_nav:
                    phone_results = phone_nav.get('results')
                elif isinstance(phone_nav, list):
                    phone_results = phone_nav

                if phone_results and len(phone_results) > 1:
                    phone_item_at_index_1 = phone_results[1]
                    if isinstance(phone_item_at_index_1, dict) and phone_item_at_index_1.get('phoneNumber'):
                        phone_number = phone_item_at_index_1['phoneNumber']
                        print(f"  ✅ Found required phone number at index 1: {phone_number}")
                    else:
                        print("  ⚠️ Item at index 1 is not a valid phone object or has no number.")
                else:
                    print("  ⚠️ Phone results list does not have an item at index 1. No other fallbacks will be used.")

                if phone_number:
                    phone_number = ''.join(filter(str.isdigit, phone_number))

                    if phone_number and len(phone_number) >= 10:
                        if not phone_number.startswith('+'):
                            if phone_number.startswith('91'):
                                phone_number = '+91' + phone_number
                            else:
                                phone_number = '+91' + phone_number
                    else:
                        print("  ⚠️ Phone number format invalid, using empty value")
                        phone_number = ""
                else:
                    print("  ⚠️ No phone number found using the strict index 1 rule.")

                print(f"  📱 Final phone number: {phone_number}")

                # Get email from the correct path
                email_nav = employee_data.get('employmentNav', {}).get('personNav', {}).get('emailNav', {})
                email = ''
                if email_nav and 'results' in email_nav:
                    email_results = email_nav['results']
                    if email_results and len(email_results) > 0:
                        # Get the primary email (isPrimary: true) or the first one
                        primary_email = None
                        for email_record in email_results:
                            if email_record.get('isPrimary', False):
                                primary_email = email_record.get('emailAddress', '')
                                break

                        if primary_email:
                            email = primary_email
                        else:
                            email = email_results[0].get('emailAddress', '')

                # Get department from the correct path
                department = ''
                department_nav = employee_data.get('departmentNav', {})
                if department_nav:
                    if 'name' in department_nav:
                        department = department_nav['name']
                    elif 'results' in department_nav:
                        dept_results = department_nav['results']
                        if dept_results and len(dept_results) > 0:
                            department = dept_results[0].get('name', '')

                # If still empty, try direct field
                if not department:
                    department = employee_data.get('department', '')

                print(f"🔍 Department: {department}")

                # Get division from the correct path
                division = ''
                division_nav = employee_data.get('divisionNav', {})
                if division_nav and 'name' in division_nav:
                    division = division_nav['name']
                else:
                    # Try direct field
                    division_results = division_nav.get('results', [])
                    if division_results:
                        division = division_results[0].get('name', '')

                # Get location from the correct path
                location = ''
                location_nav = employee_data.get('locationNav', {})
                if location_nav and 'name' in location_nav:
                    location = location_nav['name']
                else:
                    # Try direct field
                    location_results = location_nav.get('results', [])
                    if location_results:
                        location = location_results[0].get('name', '')

                print(f"🔍 Division: {division}")
                print(f"🔍 Location: {location}")

                # Get manager information with enhanced debugging
                print(f"🔍 Employee data keys: {list(employee_data.keys())}")

                # Try multiple ways to get manager ID
                manager_id = employee_data.get('managerId', '')
                if not manager_id:
                    # Try alternative paths
                    manager_id = employee_data.get('manager', '')
                if not manager_id:
                    # Try from employmentNav
                    employment_nav = employee_data.get('employmentNav', {})
                    if employment_nav:
                        manager_id = employment_nav.get('managerId', '')

                manager_name = ''
                manager_email = ''

                print(f"🔍 Raw manager ID from API: {manager_id}")
                print(f"🔍 Manager ID type: {type(manager_id)}")

                # Get manager name from managerUserNav
                manager_user_nav = employee_data.get('managerUserNav', {})
                print(f"🔍 Manager user nav: {manager_user_nav}")

                if manager_user_nav and 'defaultFullName' in manager_user_nav:
                    manager_name = manager_user_nav['defaultFullName']
                    print(f"🔍 Manager name from API: {manager_name}")
                else:
                    print(f"⚠️ No manager name found in managerUserNav")

                # If we have manager ID, fetch manager email and phone using the proven working method
                manager_phone = ''
                if manager_id and str(manager_id).strip():
                    print(f"🔍 Fetching manager email for manager ID: {manager_id}")
                    manager_email = fetch_manager_email_from_sap(manager_id)
                    if manager_email:
                        print(f"✅ Manager email fetched: {manager_email}")
                    else:
                        print(f"⚠️ Could not fetch manager email for ID: {manager_id}")
                        # Fallback: Try to construct email from manager name
                        if manager_name:
                            # Convert manager name to email format (firstname.lastname@nvtpower.com)
                            name_parts = manager_name.lower().split()
                            if len(name_parts) >= 2:
                                fallback_email = f"{name_parts[0]}.{name_parts[1]}@nvtpower.com"
                                print(f"🔄 Using fallback email format: {fallback_email}")
                                manager_email = fallback_email

                    # Fetch manager phone number
                    print(f"🔍 Fetching manager phone for manager ID: {manager_id}")
                    manager_phone = fetch_manager_phone_from_sap(manager_id)
                    if manager_phone:
                        print(f"✅ Manager phone fetched: {manager_phone}")
                    else:
                        print(f"⚠️ Could not fetch manager phone for ID: {manager_id}")
                else:
                    print(f"⚠️ No valid manager ID found for employee: {emp_code}")
                    print(f"⚠️ Manager ID value: '{manager_id}' (empty or None)")
                    print(f"🔍 Full employee data for debugging: {employee_data}")

                # Verify date of birth
                if sap_dob_formatted and dob == sap_dob_formatted:
                    # Construct full name without middle name (First Name + Last Name only)
                    employee_name = f"{first_name} {last_name}".strip()
                    # Remove extra spaces between names
                    employee_name = ' '.join(employee_name.split())

                    print(f"✅ Employee name constructed (without middle name): {employee_name}")

                    return {
                        'success': True,
                        'employee_name': employee_name,
                        'employee_email': email,
                        'employee_phone': phone_number,
                        'department': department,
                        'division': division,
                        'location': location,
                        'manager_id': manager_id,
                        'manager_name': manager_name,
                        'manager_email': manager_email,
                        'manager_phone': manager_phone
                    }
                else:
                    print(f"DOB mismatch - Expected: {sap_dob_formatted}, Received: {dob}")
                    return {'success': False, 'error': 'Invalid date of birth'}

        return {'success': False, 'error': 'Employee not found'}

    except Exception as e:
        print(f"SAP API Error: {str(e)}")
        return {'success': False, 'error': 'API connection failed'}

def clear_flash_messages():
    """Clear all flash messages from the session"""
    try:
        # Get and consume all existing flash messages to clear them
        get_flashed_messages(with_categories=True)
        # Also clear from session directly
        session.pop('_flashes', None)
    except:
        pass  # Ignore any errors in clearing flash messages

def log_login_attempt(emp_code, employee_name, success, error_message=None, ip_address=None):
    """Log login attempts"""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            c.execute('''INSERT INTO login_logs
                        (emp_code, employee_name, login_time, ip_address, success, error_message)
                        VALUES (%s, %s, %s, %s, %s, %s)''',
                     (emp_code, employee_name, datetime.now(), ip_address, success, error_message))
            conn.commit()
    finally:
        db_pool.putconn(conn)

def store_manager_info(manager_id, manager_name, manager_email, manager_phone=None, department=None):
    """Store manager information in the managers table"""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            c.execute('''INSERT INTO managers (emp_code, manager_name, manager_email, manager_phone, department)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (emp_code)
                        DO UPDATE SET
                            manager_name = EXCLUDED.manager_name,
                            manager_email = EXCLUDED.manager_email,
                            manager_phone = EXCLUDED.manager_phone,
                            department = EXCLUDED.department,
                            is_active = TRUE''',
                     (manager_id, manager_name, manager_email, manager_phone, department))
            conn.commit()
            print(f"✅ Manager info stored/updated: {manager_name} ({manager_email})")
    except Exception as e:
        print(f"❌ Error storing manager info: {str(e)}")
    finally:
        db_pool.putconn(conn)

def get_budget_info():
    """Get current budget information"""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            current_year = datetime.now().year
            c.execute('''SELECT total_budget, used_budget, remaining_budget
                        FROM budget_management
                        WHERE budget_year = %s''', (current_year,))
            budget = c.fetchone()

            if budget:
                return {
                    'total_budget': float(budget[0]),
                    'used_budget': float(budget[1]),
                    'remaining_budget': float(budget[2])
                }
            else:
                # Create default budget if not exists
                c.execute('''INSERT INTO budget_management (total_budget, used_budget, remaining_budget, budget_year)
                            VALUES (100000.00, 0.00, 100000.00, %s)''', (current_year,))
                conn.commit()
                return {
                    'total_budget': 100000.00,
                    'used_budget': 0.00,
                    'remaining_budget': 100000.00
                }
    except Exception as e:
        print(f"❌ Error getting budget info: {str(e)}")
        return {
            'total_budget': 100000.00,
            'used_budget': 0.00,
            'remaining_budget': 100000.00
        }
    finally:
        db_pool.putconn(conn)

def get_hod_budget_info_by_email(hod_email):
    """Get HOD-specific budget information from hod_budget table"""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            current_year = datetime.now().year
            c.execute('''SELECT total_budget, used_budget, remaining_budget
                        FROM hod_budget
                        WHERE hod_email = %s AND budget_year = %s''', (hod_email, current_year))
            budget = c.fetchone()

            if budget:
                return {
                    'total_budget': float(budget[0]),
                    'used_budget': float(budget[1]),
                    'remaining_budget': float(budget[2])
                }
            else:
                # Return default values if HOD budget not found
                print(f"⚠️ HOD budget not found for email: {hod_email}")
                return {
                    'total_budget': 50000.00,
                    'used_budget': 0.00,
                    'remaining_budget': 50000.00
                }
    except Exception as e:
        print(f"❌ Error getting HOD budget info: {str(e)}")
        return {
            'total_budget': 50000.00,
            'used_budget': 0.00,
            'remaining_budget': 50000.00
        }
    finally:
        db_pool.putconn(conn)

def get_hod_budget_info(hod_emp_code):
    """Get HOD budget information for a specific HOD"""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            current_year = datetime.now().year
            c.execute('''SELECT hod_emp_code, hod_name, hod_email, total_budget, used_budget, remaining_budget
                        FROM hod_budget
                        WHERE hod_emp_code = %s AND budget_year = %s''', (hod_emp_code, current_year))
            result = c.fetchone()

            if result:
                return {
                    'hod_emp_code': result[0],
                    'hod_name': result[1],
                    'hod_email': result[2],
                    'total_budget': float(result[3]),
                    'used_budget': float(result[4]),
                    'remaining_budget': float(result[5])
                }
            else:
                return None
    except Exception as e:
        print(f"❌ Error getting HOD budget info for {hod_emp_code}: {str(e)}")
        return None
    finally:
        db_pool.putconn(conn)

def get_all_hod_budgets():
    """Get budget information for all HODs"""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            current_year = datetime.now().year
            # Use explicit column names to ensure correct order
            c.execute('''SELECT
                            hod_emp_code,
                            hod_name,
                            hod_email,
                            total_budget,
                            used_budget,
                            remaining_budget
                        FROM hod_budget
                        WHERE budget_year = %s
                        ORDER BY hod_name''', (current_year,))
            results = c.fetchall()

            # Debug: Print raw database results
            print(f"🔍 Raw Database Results (first 3):")
            for i, result in enumerate(results[:3]):
                print(f"  Raw {i+1}: {result}")
                print(f"    - hod_emp_code: {result[0]}")
                print(f"    - hod_name: {result[1]}")
                print(f"    - hod_email: {result[2]}")
                print(f"    - total_budget: {result[3]}")
                print(f"    - used_budget: {result[4]}")
                print(f"    - remaining_budget: {result[5]}")

            hod_budgets = []
            for result in results:
                hod_budgets.append({
                    'hod_emp_code': result[0],
                    'hod_name': result[1],
                    'hod_email': result[2],
                    'total_budget': float(result[3]),
                    'used_budget': float(result[4]),
                    'remaining_budget': float(result[5])
                })

            return hod_budgets
    except Exception as e:
        print(f"❌ Error getting all HOD budgets: {str(e)}")
        return []
    finally:
        db_pool.putconn(conn)

def update_budget(cost):
    """Update budget when a request is approved"""
    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            current_year = datetime.now().year
            c.execute('''UPDATE budget_management
                        SET used_budget = used_budget + %s,
                            remaining_budget = remaining_budget - %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE budget_year = %s''', (cost, cost, current_year))
            conn.commit()
            print(f"✅ Budget updated: +₹{cost}")
    except Exception as e:
        print(f"❌ Error updating budget: {str(e)}")
    finally:
        db_pool.putconn(conn)

def send_own_vehicle_confirmation_email(user, reference_id):
    """Send confirmation email for own vehicle request to user only"""
    try:
        if not EMAIL_CONFIGURED:
            print("⚠️ Email not configured, skipping own vehicle confirmation email")
            return

        subject = f"Own Vehicle Request Confirmation - Reference ID: {reference_id}"

        # Create HTML email body for own vehicle confirmation
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Own Vehicle Request Confirmation</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #28a745, #20c997); color: white; padding: 20px; border-radius: 10px 10px 0 0; text-align: center; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .reference-box {{ background: #e8f5e8; border: 2px solid #28a745; border-radius: 8px; padding: 15px; margin: 20px 0; text-align: center; }}
                .reference-id {{ font-size: 24px; font-weight: bold; color: #28a745; }}
                .info-box {{ background: #d1ecf1; border: 1px solid #bee5eb; border-radius: 5px; padding: 15px; margin: 15px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2><i class="fas fa-car"></i> Own Vehicle Request Confirmed</h2>
                </div>

                <div class="content">
                    <p>Dear <strong>{user['employee_name']}</strong>,</p>

                    <p>Your own vehicle request has been successfully created and approved!</p>

                    <div class="reference-box">
                        <div class="reference-id">{reference_id}</div>
                        <p style="margin: 5px 0 0 0; color: #666;">Reference ID</p>
                    </div>

                    <div class="info-box">
                        <h4 style="color: #0c5460; margin-top: 0;"><i class="fas fa-info-circle"></i> Important Information</h4>
                        <ul style="margin: 0;">
                            <li><strong>Status:</strong> Approved (No approval required for own vehicle)</li>
                            <li><strong>Reimbursement:</strong> Company will provide reimbursement for your ride expenses</li>
                            <li><strong>Documentation:</strong> Keep receipts for expense reimbursement</li>
                            <li><strong>Reference ID:</strong> Use this ID for any queries or reimbursement claims</li>
                        </ul>
                    </div>

                    <div style="background: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px; padding: 15px; margin: 20px 0;">
                        <h4 style="color: #155724; margin-top: 0;"><i class="fas fa-check-circle"></i> Next Steps</h4>
                        <ol style="margin: 0;">
                            <li>Use your own vehicle for the required travel</li>
                            <li>Keep all receipts and expense documentation</li>
                            <li>Submit expense claims using the reference ID: <strong>{reference_id}</strong></li>
                            <li>Contact HR for reimbursement procedures</li>
                        </ol>
                    </div>

                    <p>This request has been automatically approved as it's for your own vehicle usage. No manager or admin approval is required.</p>

                    <div style="background: #e7f3ff; border: 2px solid #007bff; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                        <h4 style="color: #007bff; margin-top: 0;"><i class="fas fa-tachometer-alt"></i> Access Your Dashboard</h4>
                        <p style="margin: 10px 0;">Click the link below to view your request status and manage your taxi requests:</p>
                        <a href="{APP_URL}/" style="display: inline-block; background: linear-gradient(45deg, #007bff, #0056b3); color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                            <i class="fas fa-sign-in-alt" style="margin-right: 8px;"></i>Go to User Dashboard
                        </a>
                    </div>

                    <p>If you have any questions, please contact the Admin department with your reference ID.</p>

                    <p>Thank you for using our Taxi Management System.</p>
                </div>

                <div class="footer">
                    <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
                    <p style="margin: 0;"><em>This is an automated message. Please do not reply to this email.</em></p>
                </div>
            </div>
        </body>
        </html>"""

        send_email_flask_mail(user['employee_email'], subject, body, email_type='own_vehicle_confirmation')
        print(f"✅ Own vehicle confirmation email sent to {user['employee_email']}")

    except Exception as e:
        print(f"❌ Error sending own vehicle confirmation email: {str(e)}")

def send_feedback_reminder_email(user, request_id, travel_date, from_location, to_location, travel_time, purpose, passengers, returning_ride, return_from_location, return_to_location, return_time):
    """Send feedback reminder email to user 1 day after travel date"""
    try:
        if not EMAIL_CONFIGURED:
            print("⚠️ Email not configured, skipping feedback reminder email")
            return

        subject = f"Feedback Reminder - Taxi Request {request_id}"

        # Create HTML email body for feedback reminder
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Feedback Reminder - Taxi Request</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #ffc107, #ff8c00); color: white; padding: 20px; border-radius: 10px 10px 0 0; text-align: center; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .request-box {{ background: #fff3cd; border: 2px solid #ffc107; border-radius: 8px; padding: 15px; margin: 20px 0; }}
                .request-id {{ font-size: 20px; font-weight: bold; color: #856404; }}
                .info-box {{ background: #d1ecf1; border: 1px solid #bee5eb; border-radius: 5px; padding: 15px; margin: 15px 0; }}
                .feedback-box {{ background: #d4edda; border: 2px solid #28a745; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center; }}
                .footer {{ text-align: center; margin-top: 30px; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2><i class="fas fa-star"></i> Feedback Reminder</h2>
                </div>

                <div class="content">
                    <p>Dear <strong>{user['employee_name']}</strong>,</p>

                    <p>We hope you had a pleasant journey! Your taxi service was completed on <strong>{travel_date}</strong>.</p>

                    <div class="request-box">
                        <div class="request-id">Request ID: {request_id}</div>
                        <div style="margin: 15px 0 0 0; color: #856404;">
                            <h5 style="color: #856404; margin-bottom: 10px;"><i class="fas fa-route"></i> Journey Details</h5>

                            <!-- Outbound Journey -->
                            <div style="background: rgba(255, 255, 255, 0.7); padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #ffc107;">
                                <h6 style="color: #856404; margin: 0 0 8px 0;"><i class="fas fa-arrow-right"></i> Outbound Journey</h6>
                                <p style="margin: 5px 0; color: #856404;">
                                    <strong>From:</strong> {from_location}<br>
                                    <strong>To:</strong> {to_location}<br>
                                    <strong>Date:</strong> {travel_date}<br>
                                    <strong>Time:</strong> {travel_time}<br>
                                    <strong>Purpose:</strong> {purpose}<br>
                                    <strong>Passengers:</strong> {passengers}
                                </p>
                            </div>

                            <!-- Return Journey (if applicable) -->
                            {f'''
                            <div style="background: rgba(255, 255, 255, 0.7); padding: 12px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #28a745;">
                                <h6 style="color: #155724; margin: 0 0 8px 0;"><i class="fas fa-arrow-left"></i> Return Journey</h6>
                                <p style="margin: 5px 0; color: #155724;">
                                    <strong>From:</strong> {return_from_location}<br>
                                    <strong>To:</strong> {return_to_location}<br>
                                    <strong>Date:</strong> {travel_date}<br>
                                    <strong>Time:</strong> {return_time}
                                </p>
                            </div>
                            ''' if returning_ride == 'yes' else ''}
                        </div>
                    </div>

                    <div class="info-box">
                        <h4 style="color: #0c5460; margin-top: 0;"><i class="fas fa-info-circle"></i> Why Your Feedback Matters</h4>
                        <ul style="margin: 0;">
                            <li>Helps us improve our taxi service quality</li>
                            <li>Enables us to provide better service for future bookings</li>
                            <li>Assists in driver performance evaluation</li>
                            <li>Contributes to overall service enhancement</li>
                        </ul>
                    </div>

                    <div class="feedback-box">
                        <h4 style="color: #155724; margin-top: 0;"><i class="fas fa-comment-alt"></i> Please Share Your Experience</h4>
                        <p style="margin: 10px 0;">Your feedback is valuable to us. Please take a moment to rate your experience and share any comments.</p>
                        <a href="{APP_URL}/" style="display: inline-block; background: linear-gradient(45deg, #28a745, #20c997); color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                            <i class="fas fa-star" style="margin-right: 8px;"></i>Submit Feedback
                        </a>
                    </div>

                    <div style="background: #e7f3ff; border: 2px solid #007bff; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                        <h4 style="color: #007bff; margin-top: 0;"><i class="fas fa-tachometer-alt"></i> Access Your Dashboard</h4>
                        <p style="margin: 10px 0;">Click the link below to view your request status and submit feedback:</p>
                        <a href="{APP_URL}/" style="display: inline-block; background: linear-gradient(45deg, #007bff, #0056b3); color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                            <i class="fas fa-sign-in-alt" style="margin-right: 8px;"></i>Go to User Dashboard
                        </a>
                    </div>

                    <p><strong>Note:</strong> This feedback reminder is sent to ensure you can provide accurate feedback about your completed journey.</p>

                    <p>Thank you for using our Taxi Management System.</p>
                </div>

                <div class="footer">
                    <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
                    <p style="margin: 0;"><em>This is an automated message. Please do not reply to this email.</em></p>
                </div>
            </div>
        </body>
        </html>"""

        send_email_flask_mail(user['employee_email'], subject, body, email_type='feedback_reminder')
        print(f"✅ Feedback reminder email sent to {user['employee_email']} for request {request_id}")

    except Exception as e:
        print(f"❌ Error sending feedback reminder email: {str(e)}")

def send_feedback_reminder_whatsapp(user, request_id, travel_date, from_location, to_location, travel_time, purpose, passengers, returning_ride, return_from_location, return_to_location, return_time):
    """Send feedback reminder WhatsApp notification to user 1 day after travel date"""
    try:
        if not META_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
            print("⚠️ WhatsApp API not configured, skipping feedback reminder WhatsApp notification")
            return

        # Format user phone number for WhatsApp
        user_phone = format_phone_number(user.get('employee_phone', ''))
        if not user_phone:
            print(f"⚠️ No valid phone number available for WhatsApp feedback notification to {user['employee_name']}")
            return

        # Prepare parameters for the teximanagment_feedbac template
        # Template expects: {{1}} = employee_name, {{2}} = request_id
        parameters = [
            user['employee_name'],  # {{1}} - employee name
            request_id              # {{2}} - request ID
        ]

        # Send WhatsApp notification using the teximanagment_feedbac template
        success = send_whatsapp_template(user_phone, "teximanagment_feedbac", "en", parameters)

        if success:
            print(f"✅ Feedback reminder WhatsApp sent to {user_phone} for request {request_id}")
        else:
            print(f"❌ Failed to send feedback reminder WhatsApp to {user_phone} for request {request_id}")

    except Exception as e:
        print(f"❌ Error sending feedback reminder WhatsApp: {str(e)}")

def check_and_send_feedback_reminders():
    """Send manual feedback reminders for approved requests where travel date exceeded 24 hours (one-time only)"""
    try:
        if not EMAIL_CONFIGURED:
            print("⚠️ Email not configured, skipping manual feedback reminder check")
            return

        conn = db_pool.getconn()
        try:
            with conn.cursor() as c:
                # Get approved requests where travel date exceeded 24 hours, no feedback yet, and no manual reminder sent
                cutoff_time = datetime.now() - timedelta(hours=24)

                c.execute('''SELECT id, emp_code, employee_name, employee_email, employee_phone, department,
                                   from_location, to_location, travel_date, travel_time, purpose, passengers,
                                   status, manager_email, hod_response, hod_approval_date, admin_response, taxi_details,
                                   submission_date, admin_response_date, created_at, assigned_cost, type_of_ride,
                                   vehicle_company, vehicle_type, vehicle_number, returning_ride,
                                   return_from_location, return_to_location, return_time
                            FROM taxi_requests
                            WHERE status = 'Approved'
                            AND type_of_ride = 'company_taxi'
                            AND travel_date < %s
                            AND id NOT IN (
                                SELECT DISTINCT request_id FROM taxi_feedback
                                WHERE request_id IS NOT NULL
                            )
                            AND id NOT IN (
                                SELECT DISTINCT request_id FROM feedback_reminders
                                WHERE reminder_type = 'manual'
                            )''', (cutoff_time.date(),))

                requests_to_remind = c.fetchall()

                if requests_to_remind:
                    print(f"📧 Found {len(requests_to_remind)} approved requests with travel date > 24 hours needing manual feedback reminders")

                    for request in requests_to_remind:
                        # Create user object for email function
                        user = {
                            'employee_name': request[2],
                            'employee_email': request[3],
                            'employee_phone': request[4],
                            'department': request[5]
                        }

                        # Send feedback reminder email
                        send_feedback_reminder_email(
                            user=user,
                            request_id=request[0],
                            travel_date=request[8].strftime('%Y-%m-%d') if request[8] else 'N/A',
                            from_location=request[6],
                            to_location=request[7],
                            travel_time=request[9].strftime('%H:%M') if request[9] else 'N/A',
                            purpose=request[10] or 'N/A',
                            passengers=request[11] or 'N/A',
                            returning_ride=request[26] or 'no',
                            return_from_location=request[27] or 'N/A',
                            return_to_location=request[28] or 'N/A',
                            return_time=request[29].strftime('%H:%M') if request[29] else 'N/A'
                        )

                        # Send feedback reminder WhatsApp notification
                        send_feedback_reminder_whatsapp(
                            user=user,
                            request_id=request[0],
                            travel_date=request[8].strftime('%Y-%m-%d') if request[8] else 'N/A',
                            from_location=request[6],
                            to_location=request[7],
                            travel_time=request[9].strftime('%H:%M') if request[9] else 'N/A',
                            purpose=request[10] or 'N/A',
                            passengers=request[11] or 'N/A',
                            returning_ride=request[26] or 'no',
                            return_from_location=request[27] or 'N/A',
                            return_to_location=request[28] or 'N/A',
                            return_time=request[29].strftime('%H:%M') if request[29] else 'N/A'
                        )

                        # Mark manual reminder as sent
                        c.execute('''INSERT INTO feedback_reminders (request_id, reminder_type)
                                    VALUES (%s, %s)''', (request[0], 'manual'))

                        print(f"📧 Manual feedback reminder sent for request {request[0]} to {request[3]}")

                    conn.commit()
                else:
                    print("📧 No approved requests found with travel date > 24 hours that need manual feedback reminders")

        finally:
            db_pool.putconn(conn)

    except Exception as e:
        print(f"❌ Error checking manual feedback reminders: {str(e)}")

# Removed send_automatic_24hour_reminder function - now handled by overdue reminder scheduler

def check_and_send_overdue_reminders():
    """Check for overdue requests and send reminders (runs every 30 minutes)"""
    try:
        if not EMAIL_CONFIGURED:
            print("⚠️ Email not configured, skipping overdue reminder check")
            return

        conn = db_pool.getconn()
        try:
            with conn.cursor() as c:
                # Get approved requests where travel date was more than 24 hours ago
                cutoff_time = datetime.now() - timedelta(hours=24)

                c.execute('''SELECT id, emp_code, employee_name, employee_email, employee_phone, department,
                                   from_location, to_location, travel_date, travel_time, purpose, passengers,
                                   status, manager_email, hod_response, hod_approval_date, admin_response, taxi_details,
                                   submission_date, admin_response_date, created_at, assigned_cost, type_of_ride,
                                   vehicle_company, vehicle_type, vehicle_number, returning_ride,
                                   return_from_location, return_to_location, return_time
                            FROM taxi_requests
                            WHERE status = 'Approved'
                            AND type_of_ride = 'company_taxi'
                            AND travel_date < %s
                            AND id NOT IN (
                                SELECT DISTINCT request_id FROM feedback_reminders
                                WHERE reminder_type = 'overdue'
                            )
                            AND id NOT IN (
                                SELECT DISTINCT request_id FROM taxi_feedback
                                WHERE request_id IS NOT NULL
                            )''', (cutoff_time.date(),))

                overdue_requests = c.fetchall()

                if overdue_requests:
                    print(f"📧 Found {len(overdue_requests)} overdue requests needing reminders")

                    for request in overdue_requests:
                        # Create user object for email function
                        user = {
                            'employee_name': request[2],
                            'employee_email': request[3],
                            'employee_phone': request[4],
                            'department': request[5]
                        }

                        # Send feedback reminder email
                        send_feedback_reminder_email(
                            user=user,
                            request_id=request[0],
                            travel_date=request[8].strftime('%Y-%m-%d') if request[8] else 'N/A',
                            from_location=request[6],
                            to_location=request[7],
                            travel_time=request[9].strftime('%H:%M') if request[9] else 'N/A',
                            purpose=request[10] or 'N/A',
                            passengers=request[11] or 'N/A',
                            returning_ride=request[26] or 'no',
                            return_from_location=request[27] or 'N/A',
                            return_to_location=request[28] or 'N/A',
                            return_time=request[29].strftime('%H:%M') if request[29] else 'N/A'
                        )

                        # Send feedback reminder WhatsApp notification
                        send_feedback_reminder_whatsapp(
                            user=user,
                            request_id=request[0],
                            travel_date=request[8].strftime('%Y-%m-%d') if request[8] else 'N/A',
                            from_location=request[6],
                            to_location=request[7],
                            travel_time=request[9].strftime('%H:%M') if request[9] else 'N/A',
                            purpose=request[10] or 'N/A',
                            passengers=request[11] or 'N/A',
                            returning_ride=request[26] or 'no',
                            return_from_location=request[27] or 'N/A',
                            return_to_location=request[28] or 'N/A',
                            return_time=request[29].strftime('%H:%M') if request[29] else 'N/A'
                        )

                        # Mark overdue reminder as sent
                        c.execute('''INSERT INTO feedback_reminders (request_id, reminder_type)
                                    VALUES (%s, %s)''', (request[0], 'overdue'))

                        print(f"📧 Overdue reminder sent for request {request[0]} to {request[3]}")

                    conn.commit()
                else:
                    # Only log occasionally to reduce spam
                    import time
                    current_minute = int(time.time() / 60)
                    if current_minute % 10 == 0:  # Log every 10 minutes when no requests
                        print(f"📧 No overdue requests found needing reminders")

        finally:
            db_pool.putconn(conn)

    except Exception as e:
        print(f"❌ Error checking overdue reminders: {str(e)}")

def send_whatsapp_notification(phone_number, message):
    """Send WhatsApp notification using Facebook Graph API"""
    try:
        if not META_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
            print("⚠️ WhatsApp API not configured - skipping WhatsApp notification")
            return False

        # Clean phone number (remove any non-digit characters except +)
        clean_phone = ''.join(c for c in phone_number if c.isdigit() or c == '+')
        if not clean_phone.startswith('+'):
            # Assume Indian number if no country code
            clean_phone = '+91' + clean_phone

        url = f"{WHATSAPP_API_URL}{WHATSAPP_PHONE_NUMBER_ID}/messages"

        headers = {
            'Authorization': f'Bearer {META_ACCESS_TOKEN}',
            'Content-Type': 'application/json'
        }

        data = {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "text",
            "text": {
                "body": message
            }
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code == 200:
            print(f"✅ WhatsApp notification sent successfully to {clean_phone}")
            return True
        else:
            print(f"❌ WhatsApp notification failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error sending WhatsApp notification: {e}")
        return False

def send_email_flask_mail(to_email, subject, body, attachment_path=None, email_type='general'):
    """Send email using Flask-Mail with NVTI Mail Server"""
    try:
        # Check if email is configured
        if not EMAIL_CONFIGURED:
            print(f"⚠️ Email not configured. Skipping email to {to_email}")
            print("   Please update your .env file with proper email credentials")
            return False

        # Validate email domain for @nvtpower.com
        if not to_email.endswith('@nvtpower.com'):
            print(f"⚠️ Email domain not allowed: {to_email}")
            print("   Only @nvtpower.com emails are allowed")
            return False

        # Always send to actual recipient (production mode)
        actual_recipient = to_email
        email_subject = subject

        # Ensure the body has proper HTML structure
        if not body.strip().startswith('<!DOCTYPE html>'):
            email_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Taxi Management System</title>
</head>
<body style="font-family: Arial, sans-serif; margin: 0; padding: 0;">
    {body}
</body>
</html>"""
        else:
            email_body = body

        print(f"📧 Sending {email_type} email to actual recipient: {actual_recipient}")

        # Use application context to ensure Flask-Mail works in background tasks
        with app.app_context():
            msg = Message(
                subject=email_subject,
                recipients=[actual_recipient],
                html=email_body
            )

            if attachment_path and os.path.exists(attachment_path):
                with app.open_resource(attachment_path) as fp:
                    msg.attach(
                        filename=os.path.basename(attachment_path),
                        content_type="application/octet-stream",
                        data=fp.read()
                    )

            mail.send(msg)
            print(f"✅ Email sent successfully to {actual_recipient}")

        # Display email content in terminal for debugging
        print(f"\n📧 EMAIL CONTENT DETAILS:")
        print(f"   Subject: {email_subject}")
        print(f"   Recipient: {actual_recipient}")
        print(f"   Email Type: {email_type}")
        print(f"   Content Length: {len(email_body)} characters")

        # Extract and display key information from email body
        if email_type == 'user_confirmation':
            print(f"\n📋 USER CONFIRMATION EMAIL CONTENT:")
            # Extract request details from HTML
            import re
            request_id_match = re.search(r'Request ID:</strong></td>\s*<td[^>]*>([^<]+)</td>', email_body)
            status_match = re.search(r'Status:</strong></td>\s*<td[^>]*>([^<]+)</td>', email_body)
            from_match = re.search(r'From:</strong></td>\s*<td[^>]*>([^<]+)</td>', email_body)
            to_match = re.search(r'To:</strong></td>\s*<td[^>]*>([^<]+)</td>', email_body)
            date_match = re.search(r'Date:</strong></td>\s*<td[^>]*>([^<]+)</td>', email_body)
            time_match = re.search(r'Time:</strong></td>\s*<td[^>]*>([^<]+)</td>', email_body)

            if request_id_match:
                print(f"   Request ID: {request_id_match.group(1)}")
            if status_match:
                print(f"   Status: {status_match.group(1)}")
            if from_match:
                print(f"   From: {from_match.group(1)}")
            if to_match:
                print(f"   To: {to_match.group(1)}")
            if date_match:
                print(f"   Date: {date_match.group(1)}")
            if time_match:
                print(f"   Time: {time_match.group(1)}")

        elif email_type in ['hod_approval', 'admin_approval']:
            print(f"\n📋 {email_type.upper().replace('_', ' ')} EMAIL CONTENT:")
            # Extract key details for HOD/Admin emails
            import re
            request_id_match = re.search(r'Request ID:</strong></td>\s*<td[^>]*>([^<]+)</td>', email_body)
            employee_match = re.search(r'Employee:</strong></td>\s*<td[^>]*>([^<]+)</td>', email_body)
            department_match = re.search(r'Department:</strong></td>\s*<td[^>]*>([^<]+)</td>', email_body)

            if request_id_match:
                print(f"   Request ID: {request_id_match.group(1)}")
            if employee_match:
                print(f"   Employee: {employee_match.group(1)}")
            if department_match:
                print(f"   Department: {department_match.group(1)}")

        print(f"\n📋 EMAIL BODY PREVIEW (First 800 characters):")
        preview = email_body[:800] + "..." if len(email_body) > 800 else email_body
        print(f"   {preview}")
        print(f"\n" + "="*80)

        return True

    except Exception as e:
        print(f"❌ Email sending error: {str(e)}")
        print(f"   Check your NVTI Mail Server configuration in .env file")
        return False


# =============================================================================
# WHATSAPP INTEGRATION FUNCTIONS
# =============================================================================

def test_whatsapp_connection():
    """Test if WhatsApp API endpoint is reachable"""
    phone_number_id = os.environ.get('WHATSAPP_PHONE_NUMBER_ID')
    access_token = os.environ.get('META_ACCESS_TOKEN')

    if not phone_number_id or not access_token:
        return False

    url = f"https://graph.facebook.com/v21.0/{phone_number_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"🔍 WhatsApp API Connection Test: {resp.status_code}")
        if resp.status_code == 200:
            print("✅ WhatsApp API endpoint is reachable")
            return True
        else:
            print(f"❌ WhatsApp API endpoint returned: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"❌ WhatsApp API connection test failed: {e}")
        return False

def test_feedback_whatsapp_template():
    """Test the feedback WhatsApp template with sample data"""
    try:
        if not META_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
            print("⚠️ WhatsApp API not configured, skipping feedback template test")
            return False

        # Test with sample data
        test_user = {
            'employee_name': 'Test User',
            'employee_phone': '919999999999'  # Replace with a valid test phone number
        }
        test_request_id = 'TEST123'

        # Test the feedback reminder WhatsApp function
        print("🧪 Testing feedback WhatsApp template...")
        send_feedback_reminder_whatsapp(
            user=test_user,
            request_id=test_request_id,
            travel_date='2024-01-15',
            from_location='Test Location A',
            to_location='Test Location B',
            travel_time='10:00',
            purpose='Test Purpose',
            passengers='2',
            returning_ride='no',
            return_from_location='N/A',
            return_to_location='N/A',
            return_time='N/A'
        )

        print("✅ Feedback WhatsApp template test completed")
        return True

    except Exception as e:
        print(f"❌ Feedback WhatsApp template test failed: {e}")
        return False

def send_whatsapp_template(to_phone, template_name, lang_code, parameters):
    """
    Send a WhatsApp template message using Meta's Cloud API v21.0.
    :param to_phone: Recipient phone number in international format, e.g. '919999999999'
    :param template_name: Name of the approved template, e.g. 'user_query_submission_one_way'
    :param lang_code: Language code, e.g. 'en'
    :param parameters: List of text values for the template placeholders (in order)
    :return: True if sent, False otherwise
    """
    phone_number_id = os.environ.get('WHATSAPP_PHONE_NUMBER_ID')
    access_token = os.environ.get('META_ACCESS_TOKEN')

    # Validate environment variables
    if not phone_number_id:
        print("❌ WHATSAPP_PHONE_NUMBER_ID not found in environment variables")
        return False

    if not access_token:
        print("❌ META_ACCESS_TOKEN not found in environment variables")
        return False

    url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": lang_code}
        }
    }

    components = []

    if parameters:
        print(f"🔍 Processing parameters for template: {template_name}")
        print(f"🔍 Parameters count: {len(parameters)}")

        if template_name == "otp_login_verification" and len(parameters) >= 1:
            print(f"🔍 Using otp_login_verification template logic")
            components.append({
                "type": "body",
                "parameters": [
                    {"type": "text", "text": str(parameters[0])},
                ]
            })
            components.append({
                "type": "button",
                "sub_type": "url",
                "index": 0,
                "parameters": [{"type": "text", "text": str(parameters[0])}]
            })
        elif template_name == "user_query_submission_one_way":
            print(f"🔍 Using user_query_submission_one_way template logic")
            components.append({"type": "body", "parameters": [{"type": "text", "text": str(val)} for val in parameters]})
        elif template_name == "user_query_submission_two_way":
            print(f"🔍 Using user_query_submission_two_way template logic")
            components.append({"type": "body", "parameters": [{"type": "text", "text": str(val)} for val in parameters]})
        elif template_name == "hod_approval":
            print(f"🔍 Using hod_approval template logic")
            components.append({"type": "body", "parameters": [{"type": "text", "text": str(val)} for val in parameters]})
        elif template_name == "user_hod_approval_reject":
            print(f"🔍 Using user_hod_approval_reject template logic")
            components.append({"type": "body", "parameters": [{"type": "text", "text": str(val)} for val in parameters]})
        elif template_name == "admin_approval":
            print(f"🔍 Using admin_approval template logic")
            components.append({"type": "body", "parameters": [{"type": "text", "text": str(val)} for val in parameters]})
        elif template_name == "user_admin_approval_reject":
            print(f"🔍 Using user_admin_approval_reject template logic")
            components.append({"type": "body", "parameters": [{"type": "text", "text": str(val)} for val in parameters]})
        elif template_name == "teximanagment_feedbac":
            print(f"🔍 Using teximanagment_feedbac template logic")
            components.append({"type": "body", "parameters": [{"type": "text", "text": str(val)} for val in parameters]})
        else:
            print(f"⚠️ No template logic found for: {template_name}")
    else:
        print(f"⚠️ No parameters provided")

    if components:
        payload["template"]["components"] = components
        print(f"🔍 Components added to payload: {len(components)} components")
    else:
        print(f"⚠️ No components added to payload")

    # Debug: Print the payload being sent
    print(f"🔍 WhatsApp API Debug:")
    print(f"   URL: {url}")
    print(f"   Phone Number ID: {phone_number_id}")
    print(f"   Template: {template_name}")
    print(f"   Parameters: {parameters}")
    print(f"   Components: {components}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")

    # Retry logic for connection issues
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            print(f"WhatsApp API response (attempt {attempt + 1}): {resp.status_code} {resp.text}")
            if resp.status_code == 200:
                response_data = resp.json()
                message_id = response_data.get('messages', [{}])[0].get('id', 'N/A')
                print(f"✅ {template_name} sent successfully! Message ID: {message_id}")
                return True
            else:
                print(f"❌ Failed to send {template_name} - Status: {resp.status_code}")
                if attempt < max_retries - 1:
                    print(f"🔄 Retrying in 2 seconds... (attempt {attempt + 2}/{max_retries})")
                    time.sleep(2)
                else:
                    return False
        except requests.exceptions.ConnectionError as e:
            print(f"🔌 Connection error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                print(f"🔄 Retrying in 3 seconds... (attempt {attempt + 2}/{max_retries})")
                time.sleep(3)
            else:
                print(f"❌ Max retries reached. Failed to send {template_name}")
                return False
        except Exception as e:
            print(f"WhatsApp API error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                print(f"🔄 Retrying in 2 seconds... (attempt {attempt + 2}/{max_retries})")
                time.sleep(2)
            else:
                return False

    return False

def format_phone_number(phone):
    """Format phone number for WhatsApp (remove spaces, ensure country code)"""
    if not phone:
        return None

    # Remove all non-digit characters
    cleaned = ''.join(filter(str.isdigit, phone))

    # If it starts with 0, replace with 91 (India country code)
    if cleaned.startswith('0'):
        cleaned = '91' + cleaned[1:]

    # If it doesn't start with country code, add 91 (India)
    if not cleaned.startswith('91') and len(cleaned) == 10:
        cleaned = '91' + cleaned

    return cleaned


@app.route('/')
def index():
    # Aggressively clear any existing flash messages when accessing the home page
    try:
        # Clear flash messages multiple ways to ensure they're gone
        get_flashed_messages(with_categories=True)
        session.pop('_flashes', None)
        # Also clear any specific error messages that might be lingering
        if '_flashes' in session:
            session['_flashes'] = []
    except:
        pass

    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        emp_code = request.form.get('emp_code')
        dob = request.form.get('password')  # Keep the field name as 'password' for backward compatibility

        if not emp_code or not dob:
            flash('Please enter both employee code and date of birth', 'error')
            return render_template('login.html')

        # Check hardcoded employees first (Expats not in SAP API)
        if emp_code in HARDCODED_EMPLOYEES:
            employee = HARDCODED_EMPLOYEES[emp_code]
            # Verify DOB matches (normalize the format by removing dashes and converting to DDMMYYYY)
            normalized_input_dob = dob.replace('-', '').replace('/', '')
            normalized_stored_dob = employee['dob'].replace('-', '').replace('/', '')

            if normalized_input_dob == normalized_stored_dob:
                # Create hardcoded user session
                session['user'] = {
                    'emp_code': employee['emp_code'],
                    'employee_name': employee['employee_name'],
                    'employee_email': employee['employee_email'],
                    'employee_phone': employee['employee_phone'],
                    'department': employee['department'],
                    'division': employee.get('division', ''),
                    'location': employee.get('location', ''),
                    'manager_id': employee['manager_id'],
                    'manager_name': employee['manager_name'],
                    'manager_email': employee['manager_email'],
                    'manager_phone': employee['manager_phone'],
                    'authenticated': True,
                    'sap_last_refresh': time.time(),
                    'is_hardcoded': True  # Flag to identify hardcoded employees
                }
                apply_location_based_manager(
                    session['user'],
                    log_context=f"Login override for {emp_code}"
                )

                # Log successful hardcoded login
                log_login_attempt(emp_code, employee['employee_name'], True, ip_address=request.remote_addr)

                print(f"✅ Hardcoded employee login successful: {employee['employee_name']} ({emp_code})")
                print(f"   Department: {employee['department']}")
                print(f"   Division: {employee.get('division', 'N/A')}")
                print(f"   Location: {employee.get('location', 'N/A')}")
                print(f"   Manager: {employee['manager_name']} ({employee['manager_email']})")

                flash('Login successful!', 'success')
                return redirect(url_for('user_dashboard'))
            else:
                # Log failed login for hardcoded employee
                log_login_attempt(emp_code, employee['employee_name'], False, 'Invalid date of birth', request.remote_addr)
                flash('Login failed: Invalid date of birth', 'error')
                return render_template('login.html')

        # Special hardcoded login for employee 9024436 (Ankur Tandon) - DOB not in SAP API
        if emp_code == '9024436' and dob == '24051981,':
            # Create hardcoded user session for Ankur Tandon
            session['user'] = {
                'emp_code': '9024436',
                'employee_name': 'Ankur Tandon',
                'employee_email': 'ankur.tandon@nvtpower.com',
                'employee_phone': '9871908963',
                'department': 'Finance & Accounts',
                'manager_id': '9023422',  # Mohit Agarwal as manager for approval routing
                'manager_name': 'Mohit Agarwal',
                'manager_email': 'mohit.agarwal@nvtpower.com',
                'manager_phone': '7743967028',
                'authenticated': True,
                'sap_last_refresh': time.time()
            }
            apply_location_based_manager(
                session['user'],
                log_context="Login override for 9024436"
            )

            # Log successful hardcoded login
            log_login_attempt('9024436', 'Ankur Tandon', True, ip_address=request.remote_addr)

            flash('Login successful!', 'success')
            return redirect(url_for('user_dashboard'))

        # Special hardcoded login for employee 9017113 (Tribhuvan Agnihotri) - DOB not in SAP API
        if emp_code == '9017113' and dob == '07031962':
            # Create hardcoded user session for Tribhuvan Agnihotri
            session['user'] = {
                'emp_code': '9017113',
                'employee_name': 'Tribhuvan Agnihotri',
                'employee_email': 'tribhuvan.agnihotri@nvtpower.com',
                'employee_phone': '9871908963',
                'department': 'Management',
                'manager_id': '9023422',  # Mohit Agarwal as manager for approval routing
                'manager_name': 'Mohit Agarwal',
                'manager_email': 'mohit.agarwal@nvtpower.com',
                'manager_phone': '7743967028',
                'authenticated': True,
                'sap_last_refresh': time.time()
            }
            apply_location_based_manager(
                session['user'],
                log_context="Login override for 9017113"
            )

            # Log successful hardcoded login
            log_login_attempt('9017113', 'Tribhuvan Agnihotri', True, ip_address=request.remote_addr)

            flash('Login successful!', 'success')
            return redirect(url_for('user_dashboard'))

        # Verify credentials using SAP API
        result = verify_sap_credentials(emp_code, dob)

        if result['success']:
            # Log successful login
            log_login_attempt(emp_code, result['employee_name'], True, ip_address=request.remote_addr)

            # Store user info in session
            session['user'] = {
                'emp_code': emp_code,
                'employee_name': result['employee_name'],
                'employee_email': result['employee_email'],
                'employee_phone': result['employee_phone'],
                'department': result['department'],
                'division': result.get('division', ''),
                'location': result.get('location', ''),
                'manager_id': result.get('manager_id', ''),
                'manager_name': result.get('manager_name', ''),
                'manager_email': result.get('manager_email', ''),
                'manager_phone': result.get('manager_phone', ''),
                'authenticated': True,
                'sap_last_refresh': time.time()
            }

            # NOTIFICATION REDIRECT for special employees - keep actual manager info but redirect notifications
            special_employee_codes = ['9023649', '9025421', '9024436', '9023422', '9017113', '9021930', '9022826', '9023418', '9012706', '9025968', '9024785', '9022761', '9025802']
            if emp_code in special_employee_codes:
                # Store original manager info for display
                original_manager_id = session['user'].get('manager_id', '')
                original_manager_name = session['user'].get('manager_name', '')
                original_manager_email = session['user'].get('manager_email', '')
                original_manager_phone = session['user'].get('manager_phone', '')

                # For managers logging in as users, ensure they see their reporting manager (not themselves)
                # If the manager_id is the same as emp_code, they are seeing themselves as manager
                if original_manager_id == emp_code:
                    # Fetch their actual reporting manager from SAP API
                    actual_manager_info = fetch_actual_manager_from_sap(emp_code)
                    if actual_manager_info and actual_manager_info.get('manager_id') and actual_manager_info.get('manager_id') != emp_code:
                        # Use the actual reporting manager for display
                        session['user']['display_manager_id'] = actual_manager_info.get('manager_id', '')
                        session['user']['display_manager_name'] = actual_manager_info.get('manager_name', '')
                        session['user']['display_manager_email'] = actual_manager_info.get('manager_email', '')
                        session['user']['display_manager_phone'] = actual_manager_info.get('manager_phone', '')
                        print(f"🔄 Manager {emp_code} logging as user: Using actual reporting manager {actual_manager_info.get('manager_name', 'N/A')}")
                    else:
                        # Fallback to original info if no actual manager found
                        session['user']['display_manager_id'] = original_manager_id
                        session['user']['display_manager_name'] = original_manager_name
                        session['user']['display_manager_email'] = original_manager_email
                        session['user']['display_manager_phone'] = original_manager_phone
                        print(f"⚠️ Manager {emp_code}: No actual reporting manager found, using original info")
                else:
                    # Keep original manager info for display purposes (not self-managing)
                    session['user']['display_manager_id'] = original_manager_id
                    session['user']['display_manager_name'] = original_manager_name
                    session['user']['display_manager_email'] = original_manager_email
                    session['user']['display_manager_phone'] = original_manager_phone

                # Override notification routing to Mohit Agarwal
                session['user']['manager_id'] = '9023422'
                session['user']['manager_name'] = 'Mohit Agarwal'
                session['user']['manager_email'] = 'mohit.agrawal@nvtpower.com'
                session['user']['manager_phone'] = '7743967028'

            # Special case: Override manager for specific employees
            # These employees should have Mohit Agarwal as their manager instead of the default admin
            special_employees = [
                '9023649',  # Jayesh Sinha
                '9025421',  # Rajan Vashisht
                '9024436',  # Ankur Tandon
                '9023422',  # Mohit Agarwal (himself)
                '9017113',  # Tribhuvan Agnihotri
                '9021930',  # Brijesh Rao
                '9022826',  # Pawan Kumar Tyagi
                '9023418',  # Nishant Sharma
                '9012706',  # Manoj Saini
                '9025968',  # Vivek Saini
                '9024785',  # Vinod Kumar
                '9022761',  # Nitika Arora
                '9017113',  # Tribhuvan Agnihotri
                '9025802'   # Shivam Chaturvedi
            ]

            if emp_code in special_employees:
                print(f"🔄 Special case: Overriding manager for employee {emp_code} ({result['employee_name']})")
                session['user']['manager_id'] = '9023422'
                session['user']['manager_name'] = 'Mohit Agarwal'
                session['user']['manager_email'] = 'mohit.agarwal@nvtpower.com'
                session['user']['manager_phone'] = '7743967028'
                print(f"✅ Manager overridden to: Mohit Agarwal (mohit.agarwal@nvtpower.com)")

            location_override = apply_location_based_manager(
                session['user'],
                log_context=f"Login override for {emp_code}"
            )
            if location_override:
                print(
                    f"   Location: {session['user'].get('location', 'N/A')} | "
                    f"Department: {session['user'].get('department', 'N/A')}"
                )

            # Debug: Print manager information (after potential override)
            print(f"👤 User session created for: {result['employee_name']}")
            print(f"   Manager ID: {session['user']['manager_id']}")
            print(f"   Manager Name: {session['user']['manager_name']}")
            print(f"   Manager Email: {session['user']['manager_email']}")
            print(f"   Manager Phone: {session['user']['manager_phone']}")
            if session['user']['manager_email']:
                email_domain = session['user']['manager_email'].split('@')[1] if '@' in session['user']['manager_email'] else 'N/A'
                print(f"   Manager Email Domain: @{email_domain}")


            flash('Login successful!', 'success')
            return redirect(url_for('user_dashboard'))
        else:
            # Log failed login
            log_login_attempt(emp_code, 'Unknown', False, result.get('error', 'Invalid credentials'), request.remote_addr)
            flash(f'Login failed: {result.get("error", "Invalid credentials")}', 'error')
            return render_template('login.html')

    return render_template('login.html')

@app.route('/hod_login', methods=['GET', 'POST'])
def hod_login():
    """Robust HOD login with comprehensive error handling"""
    # Aggressively clear any existing flash messages when accessing the login page
    if request.method == 'GET':
        try:
            # Clear flash messages multiple ways to ensure they're gone
            get_flashed_messages(with_categories=True)
            session.pop('_flashes', None)
            if '_flashes' in session:
                session['_flashes'] = []
        except:
            pass

    # Initialize variables to avoid UnboundLocalError
    emp_code = ''
    dob = ''

    try:
        if request.method == 'POST':
            # Clear any existing flash messages at the start of POST request
            clear_flash_messages()

            # Input validation and sanitization
            emp_code = request.form.get('emp_code', '').strip()
            dob = request.form.get('password', '').strip()  # Keep the field name as 'password' for backward compatibility

            # Validate input
            if not emp_code:
                flash('Please enter your HOD employee code', 'error')
                return render_template('hod_login.html')

            if not dob:
                flash('Please enter your date of birth', 'error')
                return render_template('hod_login.html')

            # Validate employee code format (should be numeric)
            if not emp_code.isdigit() or len(emp_code) < 6:
                flash('Please enter a valid employee code', 'error')
                log_login_attempt(emp_code, 'Invalid Format', False, 'Invalid employee code format', request.remote_addr)
                return render_template('hod_login.html')

            # Validate DOB format (should be numeric, 6-8 digits)
            if not dob.isdigit() or len(dob) < 6 or len(dob) > 8:
                flash('Please enter a valid date of birth (DDMMYYYY or DDMMYY format)', 'error')
                log_login_attempt(emp_code, 'Invalid Format', False, 'Invalid DOB format', request.remote_addr)
                return render_template('hod_login.html')

            print(f"🔍 HOD Login attempt: {emp_code} from IP: {request.remote_addr}")

            # Special hardcoded login for employee 9017113 (Tribhuvan Agnihotri) - DOB not in SAP API
            if emp_code == '9017113' and dob == '07031962':
                # Check if this employee is authorized for HOD access
                is_authorized, hod_info = is_hod_authorized(emp_code)

                if is_authorized:
                    # Create hardcoded HOD session for Tribhuvan Agnihotri
                    session['hod'] = {
                        'emp_code': '9017113',
                        'hod_name': 'Tribhuvan Agnihotri',
                        'hod_email': 'tribhuvan.agnihotri@nvtpower.com',
                        'hod_phone': '9871908963',
                        'department': 'Management',
                        'access_level': 'full',
                        'authenticated': True
                    }

                    # Log successful hardcoded HOD login
                    log_login_attempt('9017113', 'Tribhuvan Agnihotri', True, ip_address=request.remote_addr)

                    flash('HOD login successful!', 'success')
                    return redirect(url_for('hod_dashboard'))
                else:
                    log_login_attempt(emp_code, 'Unknown', False, 'Not authorized as HOD', request.remote_addr)
                    flash('Access denied: You are not authorized as an HOD', 'error')
                    return render_template('hod_login.html')

            # All other HOD logins must go through proper SAP API validation
            # No other hardcoded logins allowed for security

        # First check if this employee is authorized for HOD access
        is_authorized, hod_info = is_hod_authorized(emp_code)

        if is_authorized:
            # Try to verify credentials using SAP API
            result = verify_sap_credentials(emp_code, dob)

            if result['success']:
                # SAP API verification successful - use SAP data
                # Log successful HOD login
                log_login_attempt(emp_code, result['employee_name'], True, ip_address=request.remote_addr)

                # Get the correct @nvtpower.com email for HOD
                correct_hod_email = get_correct_hod_email(emp_code, result['employee_email'])

                # SPECIAL HARDCODED OVERRIDE for Nishant Sharma (9023418)
                if emp_code == '9023418':
                    correct_hod_email = 'nishant.sharma@nvtpower.com'
                    print(f"🔧 HARDCODED OVERRIDE: Using correct email for Nishant Sharma: {correct_hod_email}")

                # Store HOD info in session using the new mapping system
                session['hod'] = {
                    'emp_code': emp_code,
                    'hod_name': result['employee_name'],
                    'hod_email': correct_hod_email,  # Use the correct @nvtpower.com email
                    'hod_phone': result['employee_phone'],
                    'department': hod_info.get('department', result.get('department', 'HOD Access')),
                    'access_level': hod_info.get('access_level', 'full'),
                    'manager_id': result.get('manager_id', ''),
                    'manager_name': result.get('manager_name', ''),
                    'manager_email': result.get('manager_email', ''),
                    'authenticated': True
                }

                # Clear any old flash messages before setting success message
                clear_flash_messages()
                flash('HOD login successful!', 'success')
                return redirect(url_for('hod_dashboard'))
            else:
                # SAP API failed - DOB validation failed, deny access
                print(f"❌ SAP API validation failed for HOD {emp_code}: {result.get('error', 'Unknown error')}")
                log_login_attempt(emp_code, 'Unknown', False, f'SAP API validation failed: {result.get("error", "Unknown error")}', request.remote_addr)
                flash('Invalid credentials. Please check your employee code and date of birth.', 'error')
                return render_template('hod_login.html')
        else:
            # Employee not authorized for HOD access
            log_login_attempt(emp_code, 'Unknown', False, 'Not authorized as HOD', request.remote_addr)
            flash('Access denied: You are not authorized as an HOD', 'error')
            return render_template('hod_login.html')

    except Exception as e:
        print(f"❌ Error in HOD login for emp_code '{emp_code}': {str(e)}")
        flash('An error occurred during login. Please try again.', 'error')
        return render_template('hod_login.html')

    return render_template('hod_login.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        emp_code = request.form.get('emp_code')
        dob = request.form.get('password')  # Keep the field name as 'password' for backward compatibility

        if not emp_code or not dob:
            flash('Please enter both admin code and date of birth', 'error')
            return render_template('admin_login.html')

        # Verify credentials using SAP API (same as regular login)
        result = verify_sap_credentials(emp_code, dob)

        if result['success']:
            # Check if this employee is an admin in the database
            conn = db_pool.getconn()
            try:
                with conn.cursor() as c:
                    c.execute('SELECT * FROM admins WHERE emp_code = %s AND is_active = TRUE', (emp_code,))
                    admin = c.fetchone()

                    if admin:
                        # Log successful admin login
                        log_login_attempt(emp_code, result['employee_name'], True, ip_address=request.remote_addr)

                        # Store admin info in session
                        session['admin'] = {
                            'emp_code': emp_code,
                            'admin_name': result['employee_name'],
                            'admin_email': result['employee_email'],
                            'admin_phone': result['employee_phone'],
                            'manager_id': result.get('manager_id', ''),
                            'manager_name': result.get('manager_name', ''),
                            'manager_email': result.get('manager_email', ''),
                            'authenticated': True
                        }

                        flash('Admin login successful!', 'success')
                        return redirect(url_for('admin_dashboard'))
                    else:
                        # Employee exists in SAP but not in admin table
                        log_login_attempt(emp_code, result['employee_name'], False, 'Not authorized as admin', request.remote_addr)
                        flash('Access denied: You are not authorized as an admin', 'error')
                        return render_template('admin_login.html')
            finally:
                db_pool.putconn(conn)
        else:
            # Log failed login
            log_login_attempt(emp_code, 'Unknown', False, result.get('error', 'Invalid credentials'), request.remote_addr)
            flash(f'Admin login failed: {result.get("error", "Invalid credentials")}', 'error')
            return render_template('admin_login.html')

    return render_template('admin_login.html')

def get_department_manager_for_approval(user_department):
    """Get the department-specific manager for approval routing"""
    try:
        dept_manager = get_department_manager(user_department)
        if dept_manager:
            print(f"✅ Using department manager for approval: {dept_manager['manager_name']} for department: {user_department}")
            return dept_manager
        else:
            print(f"⚠️ No department-specific manager found for: {user_department}")
            return None
    except Exception as e:
        print(f"❌ Error getting department manager for approval: {str(e)}")
        return None

# Removed process_hardcoded_hod_login function for security - all HOD logins must use SAP API validation

def get_actual_manager_for_display(emp_code, user):
    """Get the actual manager information for display purposes for special employees by fetching from SAP API"""
    try:
        print(f"🔍 Fetching actual manager from SAP API for employee: {emp_code}")

        # CHECK FOR ELECTRIC VEHICLE BUSINESS DIVISION FIRST - Override to Pawan Tyagi
        # This check overrides department-specific HOD logic
        user_division = user.get('division', '').strip().upper()
        if user_division == 'ELECTRIC VEHICLE BUSINESS' or 'ELECTRIC VEHICLE BUSINESS' in user_division:
            print(f"✅ Electric Vehicle Business Division detected for {emp_code}: Returning Pawan Tyagi as manager")
            return {
                'manager_id': '9022826',
                'manager_name': 'Pawan Tyagi',
                'manager_email': 'pawan.tyagi@nvtpower.com',
                'manager_phone': '+919765497863'
            }

        # Check if this is a special employee first - if so, don't apply department-specific logic
        special_employees = ['9023649', '9025421', '9024436', '9023422', '9017113', '9021930', '9022826', '9023418', '9012706', '9025968', '9024785', '9022761', '9025802']
        if emp_code in special_employees:
            print(f"⚠️ Employee {emp_code} is a special employee - skipping department-specific manager logic")
            return None

        # Get user's department
        user_department = user.get('department', '')

        # First check if there's a department-specific manager mapping
        dept_manager = get_department_manager(user_department)
        if dept_manager:
            print(f"✅ Found department-specific manager: {dept_manager['manager_name']} for department: {user_department}")
            return dept_manager

        # If no department-specific manager, fetch actual manager data from SAP API
        actual_manager_data = fetch_actual_manager_from_sap(emp_code)

        if actual_manager_data:
            print(f"✅ Found actual manager from SAP: {actual_manager_data['manager_name']} ({actual_manager_data['manager_email']})")
            return actual_manager_data
        else:
            print(f"⚠️ Could not fetch actual manager from SAP for {emp_code}, using fallback")
            # Fallback to original user data if SAP fetch fails
            return {
                'manager_id': user.get('manager_id', ''),
                'manager_name': user.get('manager_name', ''),
                'manager_email': user.get('manager_email', ''),
                'manager_phone': user.get('manager_phone', '')
            }

    except Exception as e:
        print(f"❌ Error in get_actual_manager_for_display: {str(e)}")
        # Fallback to original user data
        return {
            'manager_id': user.get('manager_id', ''),
            'manager_name': user.get('manager_name', ''),
            'manager_email': user.get('manager_email', ''),
            'manager_phone': user.get('manager_phone', '')
        }

def fetch_actual_manager_from_sap(emp_code):
    """Fetch the actual manager information from SAP API for display purposes"""
    try:
        print(f"🔍 Fetching actual manager from SAP for employee: {emp_code}")
        cache_key = str(emp_code).strip()
        if cache_key:
            cached_manager = _get_cached_value('actual_manager', cache_key)
            if cached_manager:
                return cached_manager

        # Use the same trimmed EmpJob query that's used in login
        url = build_empjob_url(emp_code)

        response = requests.get(
            url,
            auth=HTTPBasicAuth(SAP_CONFIG['username'], SAP_CONFIG['password']),
            timeout=12
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get('d', {}).get('results', [])

            if results:
                employee_data = results[0]

                # Get manager information
                manager_id = employee_data.get('managerId', '')
                manager_name = employee_data.get('managerUserNav', {}).get('defaultFullName', '')

                if manager_id and manager_name:
                    print(f"✅ Found manager from SAP: {manager_name} (ID: {manager_id})")

                    # Fetch manager's email and phone from SAP
                    manager_email = fetch_manager_email_from_sap(manager_id)
                    manager_phone = fetch_manager_phone_from_sap(manager_id)

                    manager_payload = {
                        'manager_id': manager_id,
                        'manager_name': manager_name,
                        'manager_email': manager_email or '',
                        'manager_phone': manager_phone or ''
                    }
                    if cache_key:
                        _set_cached_value('actual_manager', cache_key, manager_payload)
                    return manager_payload
                else:
                    print(f"⚠️ No manager found in SAP data for employee: {emp_code}")
                    return None
            else:
                print(f"⚠️ No employee data found in SAP for: {emp_code}")
                return None
        else:
            print(f"❌ SAP API error for employee {emp_code}: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error fetching actual manager from SAP for {emp_code}: {str(e)}")
        return None

def fetch_actual_employee_details_from_sap(emp_code):
    """Fetch actual employee details from SAP API for display purposes"""
    try:
        print(f"🔍 Fetching actual employee details from SAP for: {emp_code}")
        cache_key = str(emp_code).strip()
        if cache_key:
            cached_details = _get_cached_value('employee_details', cache_key)
            if cached_details:
                return cached_details

        # Use the same trimmed EmpJob query that's used in login
        url = build_empjob_url(emp_code)

        response = requests.get(
            url,
            auth=HTTPBasicAuth(SAP_CONFIG['username'], SAP_CONFIG['password']),
            timeout=12
        )

        if response.status_code == 200:
            data = response.json()
            results = data.get('d', {}).get('results', [])

            if results:
                employee_data = results[0]

                # Extract employee details
                personal_info_nav = employee_data.get('employmentNav', {}).get('personNav', {}).get('personalInfoNav', {})
                email_nav = employee_data.get('employmentNav', {}).get('personNav', {}).get('emailNav', {})
                phone_nav = employee_data.get('employmentNav', {}).get('personNav', {}).get('phoneNav', {})
                department_nav = employee_data.get('departmentNav', {})

                # Get employee name - handle both direct object and results array
                first_name = ''
                middle_name = ''
                last_name = ''

                # Check if personalInfoNav is a direct object with firstName
                if isinstance(personal_info_nav, dict) and 'firstName' in personal_info_nav:
                    first_name = personal_info_nav.get('firstName', '')
                    middle_name = personal_info_nav.get('middleName', '')
                    last_name = personal_info_nav.get('lastName', '')
                    print(f"🔍 [fetch_actual_employee] Name extracted from direct personalInfoNav object")
                # Check if personalInfoNav has a results array
                elif isinstance(personal_info_nav, dict) and 'results' in personal_info_nav:
                    results = personal_info_nav.get('results', [])
                    if results and len(results) > 0:
                        first_name = results[0].get('firstName', '')
                        middle_name = results[0].get('middleName', '')
                        last_name = results[0].get('lastName', '')
                        print(f"🔍 [fetch_actual_employee] Name extracted from personalInfoNav results array")

                # Construct employee name without middle name (First Name + Last Name only)
                employee_name = f"{first_name} {last_name}".strip()
                # Remove extra spaces between names
                employee_name = ' '.join(employee_name.split())

                print(f"✅ [fetch_actual_employee] Employee name constructed (without middle name): {employee_name}")

                # Get employee email
                employee_email = ''
                if email_nav and 'results' in email_nav:
                    email_results = email_nav['results']
                    if email_results:
                        # Look for primary email first
                        for email in email_results:
                            if email.get('isPrimary', False):
                                employee_email = email.get('emailAddress', '')
                                break

                        # If no primary email found, use first email
                        if not employee_email and email_results:
                            employee_email = email_results[0].get('emailAddress', '')

                # Get employee phone
                employee_phone = ''
                if phone_nav and 'results' in phone_nav:
                    phone_results = phone_nav['results']
                    if phone_results:
                        # Look for mobile phone first
                        for phone in phone_results:
                            phone_type = phone.get('phoneTypeNav', {}).get('picklistLabels', {}).get('results', [])
                            if phone_type and len(phone_type) > 0:
                                phone_type_label = phone_type[0].get('label', '').lower()
                                if 'mobile' in phone_type_label or 'cell' in phone_type_label:
                                    employee_phone = phone.get('phoneNumber', '')
                                    break

                        # If no mobile found, use first phone
                        if not employee_phone and phone_results:
                            employee_phone = phone_results[0].get('phoneNumber', '')

                # Get department
                department = ''
                if department_nav:
                    if 'name' in department_nav:
                        department = department_nav['name']
                    elif 'results' in department_nav:
                        dept_results = department_nav['results']
                        if dept_results and len(dept_results) > 0:
                            department = dept_results[0].get('name', '')

                # If still empty, try direct field
                if not department:
                    department = employee_data.get('department', '')

                # Get division
                division = ''
                division_nav = employee_data.get('divisionNav', {})
                if division_nav:
                    if 'name' in division_nav:
                        division = division_nav['name']
                    elif 'results' in division_nav:
                        div_results = division_nav['results']
                        if div_results and len(div_results) > 0:
                            division = div_results[0].get('name', '')

                # Get location
                location = ''
                location_nav = employee_data.get('locationNav', {})
                if location_nav:
                    if 'name' in location_nav:
                        location = location_nav['name']
                    elif 'results' in location_nav:
                        loc_results = location_nav['results']
                        if loc_results and len(loc_results) > 0:
                            location = loc_results[0].get('name', '')

                print(f"✅ Found employee details from SAP: {employee_name} ({employee_email}) - {department} - {division} - {location}")

                employee_payload = {
                    'employee_name': employee_name,
                    'employee_email': employee_email,
                    'employee_phone': employee_phone,
                    'department': department,
                    'division': division,
                    'location': location
                }
                if cache_key:
                    _set_cached_value('employee_details', cache_key, employee_payload)
                return employee_payload
            else:
                print(f"⚠️ No employee data found in SAP for: {emp_code}")
                return None
        else:
            print(f"❌ SAP API error for employee {emp_code}: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Error fetching actual employee details from SAP for {emp_code}: {str(e)}")
        return None

@app.route('/user_dashboard')
def user_dashboard():
    # Clear any existing flash messages when accessing the user dashboard
    clear_flash_messages()

    if 'user' not in session or not session['user'].get('authenticated'):
        flash('Please login first', 'error')
        return redirect(url_for('login'))

    user = session['user']

    # Enhanced manager information display for all users
    emp_code = user.get('emp_code', '')
    is_hardcoded = user.get('is_hardcoded', False)
    special_employees = ['9023649', '9025421', '9024436', '9023422', '9017113', '9021930', '9022826', '9023418', '9012706', '9025968', '9024785', '9022761', '9025802']

    sap_refresh_ttl_seconds = SAP_REFRESH_TTL_SECONDS
    last_refresh_ts = user.get('sap_last_refresh')
    should_refresh_sap = False

    if not is_hardcoded:
        missing_core_details = any(not user.get(field) for field in ['department', 'manager_email', 'employee_email'])
        if last_refresh_ts is None:
            should_refresh_sap = True
        else:
            try:
                should_refresh_sap = (time.time() - float(last_refresh_ts)) > sap_refresh_ttl_seconds
            except (TypeError, ValueError):
                should_refresh_sap = True

        if missing_core_details:
            should_refresh_sap = True

    # For hardcoded employees (Expats), use their stored manager info directly
    if is_hardcoded:
        display_manager_info = {
            'manager_id': user.get('manager_id', ''),
            'manager_name': user.get('manager_name', ''),
            'manager_email': user.get('manager_email', ''),
            'manager_phone': user.get('manager_phone', '')
        }
        print(f"🔄 Hardcoded employee {emp_code}: Using stored manager info - {display_manager_info.get('manager_name', 'N/A')}")
    # Store original manager info for display purposes
    # For special employees, show Mohit Agarwal as manager; for others, use current manager info
    elif emp_code in special_employees:
        display_manager_info = {
            'manager_id': '9023422',  # Mohit Agarwal's ID
            'manager_name': 'Mohit Agarwal',  # Mohit Agarwal
            'manager_email': 'mohit.agarwal@nvtpower.com',  # mohit.agarwal@nvtpower.com
            'manager_phone': '7743967028'  # 7743967028
        }
    else:
        display_manager_info = {
            'manager_id': user.get('manager_id', ''),
            'manager_name': user.get('manager_name', ''),
            'manager_email': user.get('manager_email', ''),
            'manager_phone': user.get('manager_phone', '')
        }

    # For non-special and non-hardcoded users, try to fetch enhanced manager information
    try:
        # Skip SAP API calls for hardcoded employees
        if not is_hardcoded:
            if should_refresh_sap:
                if emp_code not in special_employees:
                    # Get the enhanced manager info (department-specific or from SAP API)
                    enhanced_manager_info = get_actual_manager_for_display(emp_code, user)
                    if enhanced_manager_info:
                        display_manager_info = enhanced_manager_info
                        print(f"🔄 Employee {emp_code}: Displaying enhanced manager info - {enhanced_manager_info.get('manager_name', 'N/A')}")
                else:
                    print(f"🔄 Employee {emp_code}: Special employee - showing Mohit Agarwal as manager")

                # Also fetch actual employee details from SAP API for display
                actual_employee_info = fetch_actual_employee_details_from_sap(emp_code)
                if actual_employee_info:
                    # Update user data for display purposes and persist to session
                    user = {**user, **actual_employee_info}
                    session['user'].update(actual_employee_info)
                    print(f"🔄 Employee {emp_code}: Updated employee details from SAP for display")

                session['user']['sap_last_refresh'] = time.time()
            else:
                if emp_code in special_employees:
                    print(f"🔄 Employee {emp_code}: Special employee - showing Mohit Agarwal as manager")
                print(f"⏭️ Employee {emp_code}: Using cached SAP data (last refresh < {sap_refresh_ttl_seconds}s)")

    except Exception as e:
        print(f"⚠️ Error fetching enhanced manager info for {emp_code}: {str(e)}")
        # Keep original manager info if fetch fails

    user_division = user.get('division', '').strip().upper()
    # CHECK FOR ELECTRIC VEHICLE BUSINESS DIVISION - Override manager to Pawan Tyagi
    # This check overrides department-specific HOD logic
    if user_division == 'ELECTRIC VEHICLE BUSINESS' or 'ELECTRIC VEHICLE BUSINESS' in user_division:
        display_manager_info = {
            'manager_id': '9022826',
            'manager_name': 'Pawan Tyagi',
            'manager_email': 'pawan.tyagi@nvtpower.com',
            'manager_phone': '+919765497863'
        }
        # Also update session for approval routing
        session['user']['manager_id'] = '9022826'
        session['user']['manager_name'] = 'Pawan Tyagi'
        session['user']['manager_email'] = 'pawan.tyagi@nvtpower.com'
        session['user']['manager_phone'] = '+919765497863'
        print(f"✅ Electric Vehicle Business Division detected for {emp_code}: Manager set to Pawan Tyagi")

    location_override = apply_location_based_manager(
        session['user'],
        display_target=display_manager_info,
        log_context=f"User dashboard override for {emp_code}"
    )
    if location_override:
        user = session['user']

    # For special employees, keep backend routing to Mohit Agarwal (don't change session data)
    # The session data remains with Mohit Agarwal for email routing and HOD dashboard
    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            # Get requests for user - avoid all timestamp fields initially
            try:
                c.execute('''SELECT id, emp_code, employee_name, employee_email, employee_phone, department,
                                   from_location, to_location, travel_date, travel_time, purpose, passengers,
                                   status, hod_response, admin_response, taxi_details, type_of_ride,
                                   returning_ride, return_from_location, return_to_location, return_time
                            FROM taxi_requests
                            WHERE emp_code = %s
                            ORDER BY created_at DESC''', (user['emp_code'],))
                basic_requests = c.fetchall()

                # Now build the full request data with safe timestamp handling and feedback info
                requests = []
                for req in basic_requests:
                    # Convert to list to make it mutable
                    req_list = list(req)

                    # Add placeholder timestamp fields to match expected structure
                    # Current list has 21 elements (indices 0-20), so we add 4 more (indices 21-24)
                    req_list.append('N/A')  # hod_approval_date placeholder (index 21)
                    req_list.append('N/A')  # submission_date placeholder (index 22)
                    req_list.append('N/A')  # admin_response_date placeholder (index 23)
                    req_list.append('N/A')  # created_at placeholder (index 24)

                    # Try to get actual timestamp values safely
                    try:
                        c.execute('''SELECT
                                       COALESCE(hod_approval_date::text, 'N/A'),
                                       COALESCE(submission_date::text, 'N/A'),
                                       COALESCE(admin_response_date::text, 'N/A'),
                                       COALESCE(created_at::text, 'N/A')
                                   FROM taxi_requests
                                   WHERE id = %s''', (req[0],))
                        timestamps = c.fetchone()
                        if timestamps:
                            req_list[21] = timestamps[0]  # hod_approval_date
                            req_list[22] = timestamps[1]  # submission_date
                            req_list[23] = timestamps[2]  # admin_response_date
                            req_list[24] = timestamps[3]  # created_at
                    except Exception as timestamp_error:
                        print(f"Warning: Could not get timestamps for request {req[0]}: {timestamp_error}")
                        # Keep the 'N/A' placeholders

                    # Check if feedback exists for this request
                    feedback_exists = False
                    if req[12] in ['Approved', 'Own Vehicle Approved']:  # Only check for approved requests
                        try:
                            c.execute('SELECT id FROM taxi_feedback WHERE request_id = %s', (req[0],))
                            feedback_exists = c.fetchone() is not None
                        except Exception as feedback_error:
                            print(f"Warning: Could not check feedback for request {req[0]}: {feedback_error}")

                    # Add feedback info to the request tuple
                    req_list.append(feedback_exists)  # feedback_exists (index 25)

                    requests.append(tuple(req_list))

            except Exception as e:
                print(f"Error in user dashboard query: {e}")
                # Fallback to empty list if query fails completely
                requests = []

            # Get status counts
            c.execute('''SELECT status, COUNT(*)
                        FROM taxi_requests
                        WHERE emp_code = %s
                        GROUP BY status''', (user['emp_code'],))
            raw_status_counts = {status: count for status, count in c.fetchall()}

            # Process status counts to group similar statuses
            status_counts = {}
            for status, count in raw_status_counts.items():
                if status in ['Approved', 'Own Vehicle Approved']:
                    # Group both approved statuses together
                    status_counts['Approved'] = status_counts.get('Approved', 0) + count
                else:
                    status_counts[status] = count

            # Check for pending feedback (only company taxi requests without feedback)
            pending_feedback_count = 0
            for req in requests:
                if req[12] == 'Approved' and req[16] == 'company_taxi' and not req[25]:  # status, type_of_ride, and feedback_exists
                    pending_feedback_count += 1

        return render_template('user_dashboard.html', user=user, requests=requests, status_counts=status_counts, display_manager_info=display_manager_info, pending_feedback_count=pending_feedback_count)
    finally:
        db_pool.putconn(conn)

@app.route('/create_own_vehicle_request', methods=['POST'])
def create_own_vehicle_request():
    """Create an own vehicle request with auto-generated reference ID"""
    if 'user' not in session or not session['user'].get('authenticated'):
        flash('Please login first', 'error')
        return redirect(url_for('login'))

    user = session['user']

    # Check if user already has a recent own vehicle request (within last 5 minutes)
    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            recent_time = datetime.now() - timedelta(minutes=5)
            c.execute('''SELECT id FROM taxi_requests
                        WHERE emp_code = %s AND type_of_ride = 'own_vehicle'
                        AND created_at > %s''', (user['emp_code'], recent_time))
            recent_request = c.fetchone()

            if recent_request:
                print(f"⚠️ User {user['emp_code']} already has a recent own vehicle request: {recent_request[0]}")
                flash('You already have a recent own vehicle request. Please wait a few minutes before creating another.', 'info')
                return redirect(url_for('user_dashboard'))
    finally:
        db_pool.putconn(conn)

    # Generate reference ID for own vehicle request
    reference_id = f"OV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            # Insert own vehicle request directly to database
            c.execute('''INSERT INTO taxi_requests
                        (id, emp_code, employee_name, employee_email, employee_phone, department,
                         from_location, to_location, travel_date, travel_time, purpose, passengers,
                         status, manager_email, type_of_ride, submission_date, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                     (reference_id, user['emp_code'], user['employee_name'], user['employee_email'],
                      user['employee_phone'], user.get('department', ''), 'Own Vehicle', 'Own Vehicle',
                      datetime.now().date(), datetime.now().time(), 'Own Vehicle Request', 1,
                      'Own Vehicle Approved', user.get('manager_email', ''), 'own_vehicle',
                      datetime.now(), datetime.now()))

            # Insert NULL reason for own vehicle requests (user has vehicle and doesn't need taxi)
            c.execute('''INSERT INTO taxi_reason (reference_id, reason)
                        VALUES (%s, %s)''',
                     (reference_id, None))

            conn.commit()
            print(f"✅ Own vehicle request created: {reference_id}")

            # Send email only to user (no manager/admin emails)
            send_own_vehicle_confirmation_email(user, reference_id)

            flash(f'Own vehicle request created successfully! Reference ID: {reference_id}', 'success')
            return redirect(url_for('user_dashboard'))

    except Exception as e:
        print(f"❌ Error creating own vehicle request: {str(e)}")
        flash('Error creating own vehicle request. Please try again.', 'error')
        return redirect(url_for('user_dashboard'))
    finally:
        db_pool.putconn(conn)

@app.route('/submit_request', methods=['GET', 'POST'])
def submit_request():
    if 'user' not in session or not session['user'].get('authenticated'):
        flash('Please login first', 'error')
        return redirect(url_for('login'))

    # Use department-specific managers for approval routing
    user = session['user']
    emp_code = user.get('emp_code', '')
    user_department = user.get('department', '')

    user_division = user.get('division', '').strip().upper()
    # CHECK FOR ELECTRIC VEHICLE BUSINESS DIVISION - Override manager to Pawan Tyagi
    # This check overrides department-specific HOD logic
    if user_division == 'ELECTRIC VEHICLE BUSINESS' or 'ELECTRIC VEHICLE BUSINESS' in user_division:
        session['user']['manager_id'] = '9022826'
        session['user']['manager_name'] = 'Pawan Tyagi'
        session['user']['manager_email'] = 'pawan.tyagi@nvtpower.com'
        session['user']['manager_phone'] = '+919765497863'
        user = session['user']
        print(f"✅ Electric Vehicle Business Division detected for {emp_code}: Using Pawan Tyagi for approval routing")
    # Check if this is a special employee - they should always use Mohit Agarwal
    elif emp_code in ['9023649', '9025421', '9024436', '9023422', '9017113', '9021930', '9022826', '9023418', '9012706', '9025968', '9024785', '9022761', '9025802']:
        # Special employees always use Mohit Agarwal for approval routing
        session['user']['manager_id'] = '9023422'
        session['user']['manager_name'] = 'Mohit Agarwal'
        session['user']['manager_email'] = 'mohit.agarwal@nvtpower.com'
        session['user']['manager_phone'] = '7743967028'
        user = session['user']  # Update user variable with new data
        print(f"🔄 Special employee {emp_code}: Using Mohit Agarwal for approval routing")
    else:
        # Get department-specific manager for approval routing
        dept_manager = get_department_manager_for_approval(user_department)
        if dept_manager:
            # Override manager information for approval routing
            session['user']['manager_id'] = dept_manager['manager_id']
            session['user']['manager_name'] = dept_manager['manager_name']
            session['user']['manager_email'] = dept_manager['manager_email']
            session['user']['manager_phone'] = dept_manager['manager_phone']
            user = session['user']  # Update user variable with new data
            print(f"🔄 Using department manager for approval: {dept_manager['manager_name']} for department: {user_department}")
        else:
            print(f"⚠️ No department-specific manager found for: {user_department}, using default manager")

    location_override = apply_location_based_manager(
        session['user'],
        log_context=f"Submit request override for {emp_code}"
    )
    if location_override:
        user = session['user']

    # Check for pending feedback before allowing new requests
    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            # Check if user has approved company taxi requests without feedback
            c.execute('''SELECT COUNT(*) FROM taxi_requests tr
                        LEFT JOIN taxi_feedback tf ON tr.id = tf.request_id
                        WHERE tr.emp_code = %s
                        AND tr.status = 'Approved'
                        AND tr.type_of_ride = 'company_taxi'
                        AND tf.id IS NULL''', (user['emp_code'],))
            pending_feedback_count = c.fetchone()[0]

            if pending_feedback_count > 0:
                flash(f'You have {pending_feedback_count} approved request(s) pending feedback. Please submit feedback before creating new requests.', 'error')
                return redirect(url_for('user_dashboard'))

    finally:
        db_pool.putconn(conn)

    if request.method == 'POST':
        request_id = str(uuid.uuid4())[:8]

        # Get form data
        from_location = request.form.get('from_location')
        to_location = request.form.get('to_location')
        travel_date = request.form.get('travel_date')
        travel_time = request.form.get('travel_time')
        purpose = request.form.get('purpose')
        passengers = request.form.get('passengers', 1)
        type_of_ride = request.form.get('type_of_ride', 'company_taxi')
        vehicle_company = request.form.get('vehicle_company', '') or None
        vehicle_type = request.form.get('vehicle_type', '') or None
        vehicle_number = request.form.get('vehicle_number', '') or None
        returning_ride = request.form.get('returning_ride', 'no')
        return_from_location = request.form.get('return_from_location', '') or None
        return_to_location = request.form.get('return_to_location', '') or None
        return_time = request.form.get('return_time', '') or None
        taxi_reason = request.form.get('taxi_reason', '') or None

        if not all([from_location, to_location, travel_date, travel_time, purpose]):
            flash('Please fill in all required fields', 'error')
            return render_template('submit_request.html')

        # Validate return journey fields for two-way rides
        if returning_ride == 'yes':
            if not all([return_from_location, return_to_location, return_time]):
                flash('For two-way rides, please fill in all return journey details (return from, return to, and return time)', 'error')
                return render_template('submit_request.html')

        conn = db_pool.getconn()
        try:
            with conn.cursor() as c:
                print(f"🔍 Debug: Inserting taxi request with ID: {request_id}")
                print(f"🔍 Debug: User data: {user}")
                print(f"🔍 Debug: Form data: {from_location}, {to_location}, {travel_date}, {travel_time}, {purpose}, {passengers}, type_of_ride: {type_of_ride}, vehicle: {vehicle_company} {vehicle_type} {vehicle_number}, returning_ride: {returning_ride}, return_locations: {return_from_location} -> {return_to_location}, return_time: {return_time}, taxi_reason: {taxi_reason}")

                c.execute('''INSERT INTO taxi_requests
                            (id, emp_code, employee_name, employee_email, employee_phone, department,
                             from_location, to_location, travel_date, travel_time, purpose, passengers, status, manager_email, type_of_ride, vehicle_company, vehicle_type, vehicle_number, returning_ride, return_from_location, return_to_location, return_time)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                         (request_id, user['emp_code'], user['employee_name'], user['employee_email'],
                          user['employee_phone'], user['department'], from_location, to_location,
                          travel_date, travel_time, purpose, passengers, 'Pending Manager Approval', user.get('manager_email', ''), type_of_ride, vehicle_company, vehicle_type, vehicle_number, returning_ride, return_from_location, return_to_location, return_time))

                # Insert taxi reason if provided (for users who have own vehicle but need taxi)
                if taxi_reason:
                    c.execute('''INSERT INTO taxi_reason (reference_id, reason)
                                VALUES (%s, %s)''',
                             (request_id, taxi_reason))
                    print(f"✅ Debug: Taxi reason saved for request ID: {request_id}")
                else:
                    # Insert NULL reason for users who don't have vehicle or have vehicle but don't need taxi
                    c.execute('''INSERT INTO taxi_reason (reference_id, reason)
                                VALUES (%s, %s)''',
                             (request_id, None))
                    print(f"✅ Debug: NULL taxi reason saved for request ID: {request_id}")

                conn.commit()

                print(f"✅ Debug: Taxi request saved successfully with ID: {request_id}")

            # Send notification to user's manager and confirmation to user
            # Get user's manager information from session
            manager_email = user.get('manager_email', '')
            manager_name = user.get('manager_name', 'Manager')

            if manager_email:
                print(f"📧 Sending approval request to user's manager: {manager_name} ({manager_email})")

                # Store manager information in database
                store_manager_info(user.get('manager_id', ''), manager_name, manager_email, user.get('employee_phone', ''), user.get('department', ''))

                # Send email notification to user's manager
                hod_email = manager_email
                hod_name = manager_name

                # Email notification to Manager
                hod_email_subject = f"New Taxi Request - Manager Approval Required - {request_id}"
                hod_email_body = f"""<!DOCTYPE html>
                <html>
<head>
    <meta charset="UTF-8">
    <title>New Taxi Request - Manager Approval Required</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #dc3545;">
        <h2 style="color: #dc3545; margin-top: 0;">🚨 New Taxi Request - Manager Approval Required</h2>
        <p>Dear <strong>{hod_name}</strong>,</p>
        <p>A new taxi request has been submitted by your team member and requires your approval.</p>

        <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #dee2e6;">
            <h3 style="color: #495057; margin-top: 0;">📋 Request Details:</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Request ID:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #007bff;">{request_id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Employee:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{user['employee_name']} ({user['emp_code']})</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Department:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{user['department']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>From:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{from_location}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>To:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{to_location}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Date:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{travel_date}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Time:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{travel_time}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Purpose:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{purpose}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Passengers:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{passengers}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Ride Type:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{'Own Vehicle' if type_of_ride == 'own_vehicle' else 'Company Taxi'}</td>
                </tr>"""

                if type_of_ride == 'own_vehicle':
                    hod_email_body += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Vehicle Company:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{vehicle_company}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Vehicle Type:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{vehicle_type}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Vehicle Number:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{vehicle_number}</td>
                </tr>"""

                hod_email_body += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Returning Ride:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{'Yes - Two Way Ride' if returning_ride == 'yes' else 'No - One Way Ride'}</td>
                </tr>"""

                if returning_ride == 'yes':
                    hod_email_body += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return From:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_from_location}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return To:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_to_location}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return Time:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_time if return_time else 'Not specified'}</td>
                </tr>"""

                hod_email_body += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Phone:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{user['employee_phone']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>Employee Email:</strong></td>
                    <td style="padding: 8px;">{user['employee_email']}</td>
                </tr>
            </table>
        </div>

        <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border: 1px solid #ffeaa7; margin: 15px 0;">
            <p style="margin: 0;"><strong>📊 Status:</strong> <span style="color: #856404;">Pending Manager Approval</span></p>
        </div>

        <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; border: 1px solid #bee5eb; margin: 15px 0;">
            <p style="margin: 0; color: #0c5460;"><strong>⚠️ Action Required:</strong> Please review and approve/reject this request from your team member.</p>
        </div>

        <div style="background: #fff3cd; border: 2px solid #ffc107; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
            <h4 style="color: #856404; margin-top: 0;"><i class="fas fa-tachometer-alt"></i> Access Your Dashboard</h4>
            <p style="margin: 10px 0; color: #856404;">Click the link below to review and approve taxi requests:</p>
            <a href="{APP_URL}/" style="display: inline-block; background: linear-gradient(45deg, #ffc107, #e0a800); color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                <i class="fas fa-user-tie" style="margin-right: 8px;"></i>Go to HOD Dashboard
            </a>
        </div>

        <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
        <p style="font-size: 12px; color: #6c757d; text-align: center; margin: 0;">
            <em>This is an automated message from the Taxi Management System.</em>
        </p>
    </div>
                </body>
                </html>"""
                send_email_flask_mail(hod_email, hod_email_subject, hod_email_body, email_type='hod_approval')

                # Send WhatsApp notification to HOD
                try:
                    # Get manager phone number from user session (same logic as manager email)
                    manager_phone = user.get('manager_phone', '')
                    if manager_phone:
                        hod_phone = format_phone_number(manager_phone)
                        if hod_phone:
                            # Check if it's a two-way ride
                            if returning_ride == 'yes':
                                # Two-way ride: include all parameters including return details
                                hod_parameters = [
                                    hod_name,                        # {{1}} - HOD name
                                    user['employee_name'],          # {{2}} - Employee name
                                    request_id,                     # {{3}} - Reference ID
                                    from_location,                  # {{4}} - From
                                    to_location,                    # {{5}} - To
                                    travel_time,                    # {{6}} - Time
                                    travel_date,                    # {{7}} - Date
                                    return_from_location if return_from_location else 'Not specified',  # {{8}} - From (return journey)
                                    return_to_location if return_to_location else 'Not specified',      # {{9}} - To (return journey)
                                    return_time if return_time else 'Not specified',                    # {{10}} - Returning Ride time
                                ]
                            else:
                                # One-way ride: use N/A for return details
                                hod_parameters = [
                                    hod_name,                        # {{1}} - HOD name
                                    user['employee_name'],          # {{2}} - Employee name
                                    request_id,                     # {{3}} - Reference ID
                                    from_location,                  # {{4}} - From
                                    to_location,                    # {{5}} - To
                                    travel_time,                    # {{6}} - Time
                                    travel_date,                    # {{7}} - Date
                                    'N/A',                          # {{8}} - From (return journey - N/A for one-way)
                                    'N/A',                          # {{9}} - To (return journey - N/A for one-way)
                                    'N/A',                          # {{10}} - Returning Ride time (N/A for one-way)
                                ]

                            print(f"📱 Sending WhatsApp notification to HOD: {hod_phone}")
                            send_whatsapp_template(hod_phone, "hod_approval", "en", hod_parameters)
                        else:
                            print(f"⚠️ No valid phone number found for HOD: {hod_name}")
                    else:
                        print(f"⚠️ No manager phone found in user session for HOD: {hod_name}")
                except Exception as whatsapp_error:
                    print(f"❌ Error sending WhatsApp notification to HOD: {whatsapp_error}")
            else:
                print(f"⚠️ No manager email found for user: {user['employee_name']}")

            # Send confirmation email to user based on vehicle type
            user_email_subject = f"Taxi Request Submitted - Waiting for Manager Approval - {request_id}"

            if type_of_ride == 'own_vehicle':
                # Own Vehicle Email Template
                user_email_body = f"""<!DOCTYPE html>
                        <html>
<head>
    <meta charset="UTF-8">
    <title>Own Vehicle Taxi Request Submitted</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #28a745;">
        <h2 style="color: #28a745; margin-top: 0;">🚗 Own Vehicle Request Submitted Successfully</h2>
        <p>Dear <strong>{user['employee_name']}</strong>,</p>
        <p>Your own vehicle taxi request has been successfully submitted and is awaiting manager approval.</p>

        <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #dee2e6;">
            <h3 style="color: #495057; margin-top: 0;">🚗 Vehicle Information</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Vehicle Company:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{vehicle_company}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Vehicle Type:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{vehicle_type}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Vehicle Number:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{vehicle_number}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Ride Type:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #28a745; font-weight: bold;">Own Vehicle</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>Returning Ride:</strong></td>
                    <td style="padding: 8px;">{'Yes - Two Way Ride' if returning_ride == 'yes' else 'No - One Way Ride'}</td>
                </tr>
            </table>
        </div>

        <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #dee2e6;">
            <h3 style="color: #495057; margin-top: 0;">📋 Travel Details</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Request ID:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #007bff;">{request_id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>From:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{from_location}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>To:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{to_location}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Time:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{travel_time}</td>
                </tr>"""

                if returning_ride == 'yes':
                    user_email_body += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return From:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_from_location}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return To:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_to_location}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return Time:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_time if return_time else 'Not specified'}</td>
                </tr>"""

                user_email_body += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Date:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{travel_date}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Purpose:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{purpose}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>Passengers:</strong></td>
                    <td style="padding: 8px;">{passengers}</td>
                </tr>
            </table>
        </div>

        <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border: 1px solid #ffeaa7; margin: 15px 0;">
            <h4 style="color: #856404; margin-top: 0;">💰 Reimbursement Information</h4>
            <p style="margin: 0;"><strong>Note:</strong> You can submit your travel expenses for reimbursement after your trip. Please keep all receipts and submit them through the appropriate channels.</p>
        </div>

        <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border: 1px solid #ffeaa7; margin: 15px 0;">
            <p style="margin: 0;"><strong>📊 Status:</strong> <span style="color: #856404;">Waiting for Manager Approval</span></p>
        </div>

        <p>You will receive an update once your request has been reviewed by your manager.</p>

        <div style="background: #e7f3ff; border: 2px solid #007bff; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
            <h4 style="color: #007bff; margin-top: 0;"><i class="fas fa-tachometer-alt"></i> Access Your Dashboard</h4>
            <p style="margin: 10px 0;">Click the link below to review and manage taxi requests:</p>
            <a href="{APP_URL}/" style="display: inline-block; background: linear-gradient(45deg, #007bff, #0056b3); color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                <i class="fas fa-sign-in-alt" style="margin-right: 8px;"></i>Go to User Dashboard
            </a>
        </div>

        <p>Thank you for using our Taxi Management System.</p>

        <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
        <p style="font-size: 12px; color: #6c757d; text-align: center; margin: 0;">
            <em>This is an automated message. Please do not reply to this email.</em>
        </p>
    </div>
                        </body>
</html>"""
            else:
                # Company Taxi Email Template
                user_email_body = f"""<!DOCTYPE html>
                        <html>
<head>
    <meta charset="UTF-8">
    <title>Company Taxi Request Submitted</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #28a745;">
        <h2 style="color: #28a745; margin-top: 0;">🚕 Company Taxi Request Submitted Successfully</h2>
        <p>Dear <strong>{user['employee_name']}</strong>,</p>
        <p>Your company taxi request has been successfully submitted and is awaiting manager approval.</p>

        <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #dee2e6;">
            <h3 style="color: #495057; margin-top: 0;">🚕 Service Information</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Service Type:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #007bff; font-weight: bold;">Company Taxi</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>Returning Ride:</strong></td>
                    <td style="padding: 8px;">{'Yes - Two Way Ride' if returning_ride == 'yes' else 'No - One Way Ride'}</td>
                </tr>
            </table>
        </div>

        <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #dee2e6;">
            <h3 style="color: #495057; margin-top: 0;">📋 Travel Details</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Request ID:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #007bff;">{request_id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>From:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{from_location}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>To:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{to_location}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Time:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{travel_time}</td>
                </tr>"""

                if returning_ride == 'yes':
                    user_email_body += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return From:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_from_location}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return To:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_to_location}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return Time:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_time if return_time else 'Not specified'}</td>
                </tr>"""

                user_email_body += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Date:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{travel_date}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Purpose:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{purpose}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>Passengers:</strong></td>
                    <td style="padding: 8px;">{passengers}</td>
                </tr>
            </table>
        </div>

        <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; border: 1px solid #bee5eb; margin: 15px 0;">
            <h4 style="color: #0c5460; margin-top: 0;">🚕 Company Taxi Service</h4>
            <p style="margin: 0;">Your request is for company-provided taxi service. Once approved, the admin team will arrange the taxi for your travel.</p>
        </div>

        <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border: 1px solid #ffeaa7; margin: 15px 0;">
            <p style="margin: 0;"><strong>📊 Status:</strong> <span style="color: #856404;">Waiting for Manager Approval</span></p>
        </div>

        <p>You will receive an update once your request has been reviewed by your manager.</p>

        <div style="background: #e7f3ff; border: 2px solid #007bff; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
            <h4 style="color: #007bff; margin-top: 0;"><i class="fas fa-tachometer-alt"></i> Access Your Dashboard</h4>
            <p style="margin: 10px 0;">Click the link below to review and manage taxi requests:</p>
            <a href="{APP_URL}/" style="display: inline-block; background: linear-gradient(45deg, #007bff, #0056b3); color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                <i class="fas fa-sign-in-alt" style="margin-right: 8px;"></i>Go to User Dashboard
            </a>
        </div>

        <p>Thank you for using our Taxi Management System.</p>

        <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
        <p style="font-size: 12px; color: #6c757d; text-align: center; margin: 0;">
            <em>This is an automated message. Please do not reply to this email.</em>
        </p>
    </div>
                        </body>
</html>"""
            send_email_flask_mail(user['employee_email'], user_email_subject, user_email_body, email_type='user_confirmation')

            # Send WhatsApp notifications
            try:
                # Format user phone number for WhatsApp
                user_phone = format_phone_number(user.get('employee_phone', ''))
                if user_phone:
                    # Send WhatsApp notification to user
                    if returning_ride == 'yes':
                        # Two-way ride template
                        template_name = "user_query_submission_two_way"
                        parameters = [
                            user['employee_name'],  # {{1}} - Employee name
                            request_id,             # {{2}} - Reference ID
                            from_location,          # {{3}} - From
                            to_location,            # {{4}} - To
                            travel_time,            # {{5}} - Time
                            travel_date,            # {{6}} - Date
                            return_from_location,   # {{7}} - From (return journey)
                            return_to_location,     # {{8}} - To (return journey)
                            return_time             # {{9}} - Returning Ride
                        ]
                    else:
                        # One-way ride template
                        template_name = "user_query_submission_one_way"
                        parameters = [
                            user['employee_name'],  # {{1}} - Employee name
                            request_id,             # {{2}} - Reference ID
                            from_location,          # {{3}} - From
                            to_location,            # {{4}} - To
                            travel_time,            # {{5}} - Time
                            travel_date,            # {{6}} - Date
                            "One Way Ride"          # {{7}} - Type of Ride
                        ]

                    print(f"📱 Sending WhatsApp notification to user: {user_phone}")
                    send_whatsapp_template(user_phone, template_name, "en", parameters)
                else:
                    print(f"⚠️ No valid phone number found for user: {user['employee_name']}")

                # Send WhatsApp notification to HOD/Manager - COMMENTED OUT
                # manager_phone = format_phone_number(user.get('manager_phone', ''))
                # if manager_phone and manager_email:
                #     # HOD approval template
                #     template_name = "hod_approval"
                #     if returning_ride == 'yes':
                #         parameters = [
                #             manager_name,           # {{1}} - Manager name
                #             user['employee_name'],  # {{2}} - Employee name
                #             request_id,             # {{3}} - Reference ID
                #             from_location,          # {{4}} - From
                #             to_location,            # {{5}} - To
                #             travel_time,            # {{6}} - Timing
                #             travel_date,            # {{7}} - Date
                #             return_from_location,   # {{8}} - Return From
                #             return_to_location,     # {{9}} - Return To
                #             return_time             # {{10}} - Returning Ride
                #         ]
                #     else:
                #         parameters = [
                #             manager_name,           # {{1}} - Manager name
                #             user['employee_name'],  # {{2}} - Employee name
                #             request_id,             # {{3}} - Reference ID
                #             from_location,          # {{4}} - From
                #             to_location,            # {{5}} - To
                #             travel_time,            # {{6}} - Timing
                #             travel_date,            # {{7}} - Date
                #             "N/A",                  # {{8}} - Return From (N/A for one-way)
                #             "N/A",                  # {{9}} - Return To (N/A for one-way)
                #             "N/A"                   # {{10}} - Returning Ride (N/A for one-way)
                #         ]
                #
                #     print(f"📱 Sending WhatsApp notification to manager: {manager_phone}")
                #     send_whatsapp_template(manager_phone, template_name, "en", parameters)
                # else:
                #     print(f"⚠️ No valid phone number found for manager: {manager_name}")


            except Exception as e:
                print(f"❌ Error sending WhatsApp notifications: {str(e)}")
                # Don't fail the request if WhatsApp fails

            flash(f'Taxi request submitted successfully! Request ID: {request_id}', 'success')
            return redirect(url_for('user_dashboard'))

        finally:
            db_pool.putconn(conn)

    return render_template('submit_request.html')

@app.route('/hod_dashboard')
def hod_dashboard():
    if 'hod' not in session or not session['hod'].get('authenticated'):
        flash('Please login as HOD first', 'error')
        return redirect(url_for('hod_login'))

    # Clear any old flash messages when accessing the dashboard
    clear_flash_messages()
    # Clear flash messages multiple times to ensure they're gone
    try:
        get_flashed_messages(with_categories=True)
        session.pop('_flashes', None)
    except:
        pass

    hod = session['hod']
    hod_email = hod.get('hod_email', '')
    hod_emp_code = hod.get('emp_code', '')

    # SPECIAL HARDCODED OVERRIDE for Nishant Sharma (9023418) - Force correct email
    if hod_emp_code == '9023418':
        hod_email = 'nishant.sharma@nvtpower.com'
        print(f"🔧 HOD DASHBOARD OVERRIDE: Forcing correct email for Nishant Sharma: {hod_email}")
        # Update session with correct email
        session['hod']['hod_email'] = hod_email

    # Check if this is the master login (employee 9025857)
    is_master_login = (hod_emp_code == '9025857')

    # Debug logging
    print(f"🔍 HOD Dashboard - HOD Email: {hod_email}")
    print(f"🔍 HOD Dashboard - HOD Name: {hod.get('hod_name', 'Unknown')}")
    print(f"🔍 HOD Dashboard - HOD Emp Code: {hod_emp_code}")
    print(f"🔍 HOD Dashboard - Master Login: {is_master_login}")

    # Get status filter from URL parameters
    status_filter = request.args.get('status', '')

    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            # Build query based on status filter and master login status
            if is_master_login:
                # Master login (9025857) - Show ALL requests
                if status_filter == 'pending':
                    query = '''SELECT id, emp_code, employee_name, employee_email, employee_phone, department,
                                       from_location, to_location, travel_date, travel_time, purpose, passengers,
                                       status, manager_email, hod_response, hod_approval_date, admin_response, taxi_details,
                                       submission_date, admin_response_date, created_at, assigned_cost, type_of_ride,
                                       vehicle_company, vehicle_type, vehicle_number, returning_ride,
                                       return_from_location, return_to_location, return_time
                                FROM taxi_requests
                                WHERE status = 'Pending Manager Approval'
                                AND (hod_response IS NULL OR hod_response = '')
                                AND travel_date IS NOT NULL
                                AND travel_date >= '1900-01-01'
                                AND travel_date <= '2100-12-31'
                                ORDER BY COALESCE(submission_date, created_at) DESC'''
                elif status_filter == 'approved':
                    query = '''SELECT id, emp_code, employee_name, employee_email, employee_phone, department,
                                       from_location, to_location, travel_date, travel_time, purpose, passengers,
                                       status, manager_email, hod_response, hod_approval_date, admin_response, taxi_details,
                                       submission_date, admin_response_date, created_at, assigned_cost, type_of_ride,
                                       vehicle_company, vehicle_type, vehicle_number, returning_ride,
                                       return_from_location, return_to_location, return_time
                                FROM taxi_requests
                                WHERE ((status = 'Pending Admin Approval' AND hod_response IS NOT NULL)
                                   OR (status = 'Approved' AND hod_response IS NOT NULL))
                                AND travel_date IS NOT NULL
                                AND travel_date >= '1900-01-01'
                                AND travel_date <= '2100-12-31'
                                ORDER BY COALESCE(submission_date, created_at) DESC'''
                elif status_filter == 'rejected':
                    query = '''SELECT id, emp_code, employee_name, employee_email, employee_phone, department,
                                       from_location, to_location, travel_date, travel_time, purpose, passengers,
                                       status, manager_email, hod_response, hod_approval_date, admin_response, taxi_details,
                                       submission_date, admin_response_date, created_at, assigned_cost, type_of_ride,
                                       vehicle_company, vehicle_type, vehicle_number, returning_ride,
                                       return_from_location, return_to_location, return_time
                                FROM taxi_requests
                                WHERE status = 'Rejected'
                                AND hod_response IS NOT NULL
                                AND travel_date IS NOT NULL
                                AND travel_date >= '1900-01-01'
                                AND travel_date <= '2100-12-31'
                                ORDER BY COALESCE(submission_date, created_at) DESC'''
                else:
                    # Show all requests for master login
                    query = '''SELECT id, emp_code, employee_name, employee_email, employee_phone, department,
                                       from_location, to_location, travel_date, travel_time, purpose, passengers,
                                       status, manager_email, hod_response, hod_approval_date, admin_response, taxi_details,
                                       submission_date, admin_response_date, created_at, assigned_cost, type_of_ride,
                                       vehicle_company, vehicle_type, vehicle_number, returning_ride,
                                       return_from_location, return_to_location, return_time
                                FROM taxi_requests
                                WHERE ((status = 'Pending Manager Approval' AND (hod_response IS NULL OR hod_response = ''))
                                   OR (status = 'Pending Admin Approval' AND hod_response IS NOT NULL)
                                   OR (status = 'Approved' AND hod_response IS NOT NULL)
                                   OR (status = 'Rejected' AND hod_response IS NOT NULL))
                                AND travel_date IS NOT NULL
                                AND travel_date >= '1900-01-01'
                                AND travel_date <= '2100-12-31'
                                ORDER BY COALESCE(submission_date, created_at) DESC'''
                query_params = []
            else:
                # Regular HOD - Only show requests where manager_email matches HOD's email
                if status_filter == 'pending':
                    # Show only pending requests for this HOD's direct reports
                    query = '''SELECT id, emp_code, employee_name, employee_email, employee_phone, department,
                                       from_location, to_location, travel_date, travel_time, purpose, passengers,
                                       status, manager_email, hod_response, hod_approval_date, admin_response, taxi_details,
                                       submission_date, admin_response_date, created_at, assigned_cost, type_of_ride,
                                       vehicle_company, vehicle_type, vehicle_number, returning_ride,
                                       return_from_location, return_to_location, return_time
                                FROM taxi_requests
                                WHERE status = 'Pending Manager Approval'
                                AND (hod_response IS NULL OR hod_response = '')
                                AND manager_email = %s
                                AND travel_date IS NOT NULL
                                AND travel_date >= '1900-01-01'
                                AND travel_date <= '2100-12-31'
                                ORDER BY COALESCE(submission_date, created_at) DESC'''
                elif status_filter == 'approved':
                    query = '''SELECT id, emp_code, employee_name, employee_email, employee_phone, department,
                                       from_location, to_location, travel_date, travel_time, purpose, passengers,
                                       status, manager_email, hod_response, hod_approval_date, admin_response, taxi_details,
                                       submission_date, admin_response_date, created_at, assigned_cost, type_of_ride,
                                       vehicle_company, vehicle_type, vehicle_number, returning_ride,
                                       return_from_location, return_to_location, return_time
                                FROM taxi_requests
                                WHERE ((status = 'Pending Admin Approval' AND hod_response IS NOT NULL)
                                   OR (status = 'Approved' AND hod_response IS NOT NULL))
                                AND manager_email = %s
                                AND travel_date IS NOT NULL
                                AND travel_date >= '1900-01-01'
                                AND travel_date <= '2100-12-31'
                                ORDER BY COALESCE(submission_date, created_at) DESC'''
                elif status_filter == 'rejected':
                    query = '''SELECT id, emp_code, employee_name, employee_email, employee_phone, department,
                                       from_location, to_location, travel_date, travel_time, purpose, passengers,
                                       status, manager_email, hod_response, hod_approval_date, admin_response, taxi_details,
                                       submission_date, admin_response_date, created_at, assigned_cost, type_of_ride,
                                       vehicle_company, vehicle_type, vehicle_number, returning_ride,
                                       return_from_location, return_to_location, return_time
                                FROM taxi_requests
                                WHERE status = 'Rejected'
                                AND hod_response IS NOT NULL
                                AND manager_email = %s
                                AND travel_date IS NOT NULL
                                AND travel_date >= '1900-01-01'
                                AND travel_date <= '2100-12-31'
                                ORDER BY COALESCE(submission_date, created_at) DESC'''
                else:
                    # Show all requests (default) for this HOD's direct reports
                    query = '''SELECT id, emp_code, employee_name, employee_email, employee_phone, department,
                                       from_location, to_location, travel_date, travel_time, purpose, passengers,
                                       status, manager_email, hod_response, hod_approval_date, admin_response, taxi_details,
                                       submission_date, admin_response_date, created_at, assigned_cost, type_of_ride,
                                       vehicle_company, vehicle_type, vehicle_number, returning_ride,
                                       return_from_location, return_to_location, return_time
                                FROM taxi_requests
                                WHERE ((status = 'Pending Manager Approval' AND (hod_response IS NULL OR hod_response = ''))
                                   OR (status = 'Pending Admin Approval' AND hod_response IS NOT NULL)
                                   OR (status = 'Approved' AND hod_response IS NOT NULL)
                                   OR (status = 'Rejected' AND hod_response IS NOT NULL))
                                AND manager_email = %s
                                AND travel_date IS NOT NULL
                                AND travel_date >= '1900-01-01'
                                AND travel_date <= '2100-12-31'
                                ORDER BY COALESCE(submission_date, created_at) DESC'''
                query_params = [hod_email]

            try:
                if is_master_login:
                    # Master login - Execute query directly without manager_email filtering
                    print(f"🔍 Master Login - Executing query for ALL requests")
                    c.execute(query, query_params)
                    basic_requests = c.fetchall()
                    print(f"🔍 Master Login - Found {len(basic_requests)} requests")
                else:
                    # Regular HOD - Use flexible matching but respect status filter
                    print(f"🔍 Regular HOD - Looking for requests with manager_email: {hod_email}")
                    print(f"🔍 Regular HOD - Status filter: {status_filter}")

                    # Check if this HOD is Mohit Agarwal - if so, also include special employee requests
                    special_employees = ['9023649', '9025421', '9024436', '9023422', '9017113', '9021930', '9022826', '9023418', '9012706', '9025968', '9024785', '9022761', '9025802']
                    is_mohit_agarwal = (hod_emp_code == '9023422')

                    if is_mohit_agarwal:
                        print(f"🔍 HOD is Mohit Agarwal - Will include special employee requests")
                        # For Mohit Agarwal, get requests for both his direct reports AND special employees
                        matching_requests = find_matching_requests_for_hod(hod_email, c)

                        # Also get requests from special employees
                        special_emp_placeholders = ','.join(['%s'] * len(special_employees))
                        c.execute(f'''SELECT id, emp_code, employee_name, manager_email, status
                                     FROM taxi_requests
                                     WHERE emp_code IN ({special_emp_placeholders})''', special_employees)
                        special_employee_requests = c.fetchall()

                        # Combine both sets of requests
                        all_matching_requests = matching_requests + special_employee_requests
                        # Remove duplicates based on request ID
                        seen_ids = set()
                        unique_requests = []
                        for req in all_matching_requests:
                            if req[0] not in seen_ids:
                                unique_requests.append(req)
                                seen_ids.add(req[0])
                        matching_requests = unique_requests
                        print(f"🔍 Mohit Agarwal - Found {len(matching_requests)} total requests (including special employees)")
                    else:
                        # Use flexible matching to find requests for this HOD
                        matching_requests = find_matching_requests_for_hod(hod_email, c)

                    if matching_requests:
                        # Get the full request details for matching requests with status filter
                        request_ids = [req[0] for req in matching_requests]
                        placeholders = ','.join(['%s'] * len(request_ids))

                        # Build the full query with the matching request IDs and status filter
                        if status_filter == 'pending':
                            status_condition = "AND status = 'Pending Manager Approval' AND (hod_response IS NULL OR hod_response = '')"
                        elif status_filter == 'approved':
                            status_condition = "AND ((status = 'Pending Admin Approval' AND hod_response IS NOT NULL) OR (status = 'Approved' AND hod_response IS NOT NULL))"
                        elif status_filter == 'rejected':
                            status_condition = "AND status = 'Rejected' AND hod_response IS NOT NULL"
                        else:
                            status_condition = "AND ((status = 'Pending Manager Approval' AND (hod_response IS NULL OR hod_response = '')) OR (status = 'Pending Admin Approval' AND hod_response IS NOT NULL) OR (status = 'Approved' AND hod_response IS NOT NULL) OR (status = 'Rejected' AND hod_response IS NOT NULL))"

                        full_query = f'''SELECT id, emp_code, employee_name, employee_email, employee_phone, department,
                                               from_location, to_location, travel_date, travel_time, purpose, passengers,
                                               status, manager_email, hod_response, hod_approval_date, admin_response, taxi_details,
                                               submission_date, admin_response_date, created_at, assigned_cost, type_of_ride,
                                               vehicle_company, vehicle_type, vehicle_number, returning_ride,
                                               return_from_location, return_to_location, return_time
                                        FROM taxi_requests
                                        WHERE id IN ({placeholders})
                                        {status_condition}
                                        ORDER BY COALESCE(submission_date, created_at) DESC'''

                        c.execute(full_query, request_ids)
                        basic_requests = c.fetchall()
                        print(f"🔍 Found {len(basic_requests)} filtered request details for HOD email: {hod_email}")
                    else:
                        # Fallback to original query if no flexible matches found
                        print(f"🔍 Regular HOD - Using fallback query")
                        print(f"🔍 Regular HOD - Query: {query}")
                        print(f"🔍 Regular HOD - Query Params: {query_params}")
                        c.execute(query, query_params)
                        basic_requests = c.fetchall()
                        print(f"🔍 Found {len(basic_requests)} requests using original query for HOD email: {hod_email}")

                # Now build the full request data with safe timestamp handling
                requests = []
                for req in basic_requests:
                    # Convert to list to make it mutable
                    req_list = list(req)

                    # Get submission date safely
                    submission_date = 'N/A'
                    try:
                        c.execute('''SELECT COALESCE(submission_date::text, 'N/A')
                                   FROM taxi_requests
                                   WHERE id = %s''', (req[0],))
                        timestamp_result = c.fetchone()
                        if timestamp_result:
                            submission_date = timestamp_result[0]
                    except Exception as timestamp_error:
                        print(f"Warning: Could not get timestamp for request {req[0]}: {timestamp_error}")

                    # Build the final request tuple to match template expectations
                    # [0-14] = basic fields, [15] = submission_date
                    final_request = req_list + [submission_date]

                    requests.append(tuple(final_request))

            except Exception as e:
                print(f"Error in HOD dashboard query: {e}")
                # Fallback to empty list if query fails completely
                requests = []

            # Get status counts based on master login status
            if is_master_login:
                # Master login - Get counts for ALL requests
                print(f"🔍 Master Login - Getting status counts for ALL requests")
                c.execute('''SELECT status, COUNT(*)
                            FROM taxi_requests
                            WHERE travel_date IS NOT NULL
                            AND travel_date >= '1900-01-01'
                            AND travel_date <= '2100-12-31'
                            GROUP BY status''')
                status_counts = {status: count for status, count in c.fetchall()}

                c.execute('''SELECT COUNT(*)
                            FROM taxi_requests
                            WHERE status = 'Pending Manager Approval'
                            AND (hod_response IS NULL OR hod_response = '')
                            AND travel_date IS NOT NULL
                            AND travel_date >= '1900-01-01'
                            AND travel_date <= '2100-12-31' ''')
                pending_hod_count = c.fetchone()[0]
            else:
                # Regular HOD - Get status counts for requests under this HOD only using flexible matching
                matching_requests_for_counts = find_matching_requests_for_hod(hod_email, c)
                if matching_requests_for_counts:
                    request_ids_for_counts = [req[0] for req in matching_requests_for_counts]
                    placeholders_for_counts = ','.join(['%s'] * len(request_ids_for_counts))

                    c.execute(f'''SELECT status, COUNT(*)
                                FROM taxi_requests
                                WHERE id IN ({placeholders_for_counts})
                                GROUP BY status''', request_ids_for_counts)
                    status_counts = {status: count for status, count in c.fetchall()}

                    c.execute(f'''SELECT COUNT(*)
                                FROM taxi_requests
                                WHERE status = 'Pending Manager Approval'
                                AND (hod_response IS NULL OR hod_response = '')
                                AND id IN ({placeholders_for_counts})''', request_ids_for_counts)
                    pending_hod_count = c.fetchone()[0]
                else:
                    # Fallback to original query
                    c.execute('''SELECT status, COUNT(*)
                                FROM taxi_requests
                                WHERE LOWER(TRIM(manager_email)) = %s
                                AND travel_date IS NOT NULL
                                AND travel_date >= '1900-01-01'
                                AND travel_date <= '2100-12-31'
                                GROUP BY status''', (normalize_email_for_matching(hod_email),))
                    status_counts = {status: count for status, count in c.fetchall()}

                    c.execute('''SELECT COUNT(*)
                                FROM taxi_requests
                                WHERE status = 'Pending Manager Approval'
                                AND (hod_response IS NULL OR hod_response = '')
                                AND LOWER(TRIM(manager_email)) = %s
                                AND travel_date IS NOT NULL
                                AND travel_date >= '1900-01-01'
                                AND travel_date <= '2100-12-31' ''', (normalize_email_for_matching(hod_email),))
                    pending_hod_count = c.fetchone()[0]

            print(f"🔍 Status counts for HOD {hod_email}: {status_counts}")
            print(f"🔍 Pending HOD count for {hod_email}: {pending_hod_count}")

            # Get budget information from hod_budget table
            current_year = datetime.now().year
            c.execute('''SELECT total_budget, used_budget, remaining_budget
                        FROM hod_budget
                        WHERE hod_email = %s AND budget_year = %s''', (hod_email, current_year))
            budget_info = c.fetchone()

            # If no budget found, create default budget entry
            if not budget_info:
                c.execute('''INSERT INTO hod_budget (hod_emp_code, hod_name, hod_email, total_budget, used_budget, remaining_budget, budget_year)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (hod_emp_code, budget_year) DO NOTHING''',
                            (hod_emp_code, hod.get('hod_name', 'Unknown'), hod_email, 50000.00, 0.00, 50000.00, current_year))
                conn.commit()

                # Fetch the newly created budget
                c.execute('''SELECT total_budget, used_budget, remaining_budget
                            FROM hod_budget
                            WHERE hod_email = %s AND budget_year = %s''', (hod_email, current_year))
                budget_info = c.fetchone()

            # Ensure budget_info is never None - provide default values
            if not budget_info:
                budget_info = (50000.00, 0.00, 50000.00)  # (total, used, remaining)

            # Calculate budget percentage
            budget_percentage = 0
            if budget_info and budget_info[0] > 0:
                budget_percentage = (budget_info[1] / budget_info[0]) * 100

        return render_template('hod_dashboard.html', requests=requests, status_counts=status_counts, pending_hod_count=pending_hod_count, status_filter=status_filter, is_master_login=is_master_login, budget_info=budget_info, budget_percentage=budget_percentage, current_year=current_year)
    finally:
        db_pool.putconn(conn)

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin' not in session or not session['admin'].get('authenticated'):
        flash('Please login as admin first', 'error')
        return redirect(url_for('admin_login'))

    # Get filter parameters from request
    status_filter = request.args.get('status', '')
    department_filter = request.args.get('department', '')
    employee_filter = request.args.get('employee', '')

    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            # Build the base query
            base_query = '''SELECT id, emp_code, employee_name, employee_email, employee_phone, department,
                                   from_location, to_location, travel_date, travel_time, purpose, passengers,
                                   status, hod_response, admin_response, taxi_details, assigned_cost, type_of_ride,
                                   vehicle_company, vehicle_type, vehicle_number, returning_ride,
                                   return_from_location, return_to_location, return_time
                            FROM taxi_requests
                            WHERE status IN ('Pending Admin Approval', 'Approved', 'Rejected')
                            AND hod_response IS NOT NULL
                            AND hod_response != '' '''

            # Add filters based on parameters
            query_params = []

            if status_filter:
                base_query += ' AND status = %s'
                query_params.append(status_filter)

            if department_filter:
                base_query += ' AND department = %s'
                query_params.append(department_filter)

            if employee_filter:
                base_query += ' AND (employee_name ILIKE %s OR emp_code ILIKE %s)'
                employee_pattern = f'%{employee_filter}%'
                query_params.extend([employee_pattern, employee_pattern])

            base_query += ' ORDER BY submission_date DESC'

            # Get only requests that have been approved by HOD and need admin action
            try:
                c.execute(base_query, query_params)
                basic_requests = c.fetchall()

                # Now build the full request data with safe timestamp handling
                requests = []
                for req in basic_requests:
                    # Convert to list to make it mutable
                    req_list = list(req)

                    # Add placeholder timestamp fields to match expected structure
                    # Current list has 24 elements (indices 0-23), so we add 4 more (indices 24-27)
                    req_list.append('N/A')  # hod_approval_date placeholder (index 24)
                    req_list.append('N/A')  # submission_date placeholder (index 25)
                    req_list.append('N/A')  # admin_response_date placeholder (index 26)
                    req_list.append('N/A')  # created_at placeholder (index 27)

                    # Try to get actual timestamp values safely
                    try:
                        c.execute('''SELECT
                                       COALESCE(hod_approval_date::text, 'N/A'),
                                       COALESCE(submission_date::text, 'N/A'),
                                       COALESCE(admin_response_date::text, 'N/A'),
                                       COALESCE(created_at::text, 'N/A')
                                   FROM taxi_requests
                                   WHERE id = %s''', (req[0],))
                        timestamps = c.fetchone()
                        if timestamps:
                            req_list[24] = timestamps[0]  # hod_approval_date
                            req_list[25] = timestamps[1]  # submission_date
                            req_list[26] = timestamps[2]  # admin_response_date
                            req_list[27] = timestamps[3]  # created_at
                    except Exception as timestamp_error:
                        print(f"Warning: Could not get timestamps for request {req[0]}: {timestamp_error}")
                        # Keep the 'N/A' placeholders

                    requests.append(tuple(req_list))

            except Exception as e:
                print(f"Error in admin dashboard query: {e}")
                # Fallback to empty list if query fails completely
                requests = []


            # Get status counts for requests that should be visible to admin
            c.execute('''SELECT status, COUNT(*)
                        FROM taxi_requests
                        WHERE status IN ('Pending Admin Approval', 'Approved', 'Rejected')
                        AND hod_response IS NOT NULL
                        AND hod_response != ''
                        GROUP BY status''')
            status_counts = {status: count for status, count in c.fetchall()}

            # Get pending admin approval count
            pending_admin_count = status_counts.get('Pending Admin Approval', 0)

            # Get budget information
            budget_info = get_budget_info()
            budget_percentage = (budget_info['used_budget'] / budget_info['total_budget'] * 100) if budget_info['total_budget'] > 0 else 0

        return render_template('admin_dashboard.html', requests=requests, status_counts=status_counts, pending_admin_count=pending_admin_count, budget_info=budget_info, budget_percentage=budget_percentage)
    finally:
        db_pool.putconn(conn)

@app.route('/hod_response/<request_id>', methods=['GET', 'POST'])
def hod_response(request_id):
    if 'hod' not in session or not session['hod'].get('authenticated'):
        flash('Please login as HOD first', 'error')
        return redirect(url_for('hod_login'))

    hod = session['hod']
    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            # Get basic request data first
            c.execute('''SELECT id, emp_code, employee_name, employee_email, employee_phone, department,
                               from_location, to_location, travel_date, travel_time, purpose, passengers,
                               status, manager_email, hod_response, hod_approval_date, admin_response, taxi_details,
                               submission_date, admin_response_date, created_at, assigned_cost, type_of_ride,
                               vehicle_company, vehicle_type, vehicle_number, returning_ride,
                               return_from_location, return_to_location, return_time
                        FROM taxi_requests WHERE id = %s''', (request_id,))
            basic_request = c.fetchone()

            # Get taxi reason from taxi_reason table
            taxi_reason = None
            if basic_request:
                c.execute('''SELECT reason FROM taxi_reason WHERE reference_id = %s''', (request_id,))
                reason_result = c.fetchone()
                taxi_reason = reason_result[0] if reason_result else None

            if basic_request:
                # All fields are now included in the main query, so we can use the data directly
                taxi_request = basic_request
            else:
                taxi_request = None

            if not taxi_request:
                flash('Request not found', 'error')
                return redirect(url_for('hod_dashboard'))

            # HOD can approve requests from any department (removed department restriction)

            # Check if request is in pending status (either 'Pending Manager Approval' or 'Pending')
            if taxi_request[12] not in ['Pending Manager Approval', 'Pending']:
                flash('This request is not pending manager approval', 'error')
                return redirect(url_for('hod_dashboard'))

            if request.method == 'POST':
                hod_action = request.form.get('hod_action')  # 'approve' or 'reject'
                hod_response = request.form.get('hod_response')

                print(f"HOD Action: {hod_action}")
                print(f"HOD Response: {hod_response}")
                print(f"Request ID: {request_id}")

                if not all([hod_action, hod_response]):
                    flash('Please fill in all required fields', 'error')
                    budget_info = get_hod_budget_info_by_email(hod['hod_email'])
                    return render_template('hod_response.html', request=taxi_request, taxi_reason=taxi_reason, budget_info=budget_info)

                # Check budget before allowing approval
                if hod_action == 'approve':
                    # Get HOD-specific budget information
                    budget_info = get_hod_budget_info_by_email(hod['hod_email'])
                    remaining_budget = budget_info['remaining_budget']

                    # Check if remaining budget is less than 500
                    if remaining_budget < 500:
                        flash(f'Cannot approve request: Your remaining budget (₹{remaining_budget:,.2f}) is less than ₹500. Please contact admin to increase budget.', 'error')
                        return render_template('hod_response.html', request=taxi_request, taxi_reason=taxi_reason, budget_info=budget_info)

                    new_status = 'Pending Admin Approval'
                    status_message = 'Approved by HOD'
                else:
                    new_status = 'Rejected'
                    status_message = 'Rejected by HOD'

                try:
                    # Update request
                    c.execute('''UPDATE taxi_requests
                                SET status = %s, hod_response = %s, hod_approval_date = %s
                                WHERE id = %s''',
                             (new_status, hod_response, datetime.now(), request_id))
                    conn.commit()

                    # Send notification based on HOD action
                    employee_email = taxi_request[3]
                    employee_phone = taxi_request[4]
                    employee_name = taxi_request[2]

                    # Only send email to user if HOD rejected the request
                    if hod_action == 'reject':
                        # Extract additional fields from taxi_request for HOD rejection email
                        type_of_ride = taxi_request[TYPE_OF_RIDE] if len(taxi_request) > TYPE_OF_RIDE else 'company_taxi'
                        returning_ride = taxi_request[RETURNING_RIDE] if len(taxi_request) > RETURNING_RIDE else 'no'
                        return_from_location = taxi_request[RETURN_FROM_LOCATION] if len(taxi_request) > RETURN_FROM_LOCATION else ''
                        return_to_location = taxi_request[RETURN_TO_LOCATION] if len(taxi_request) > RETURN_TO_LOCATION else ''
                        return_time = taxi_request[RETURN_TIME] if len(taxi_request) > RETURN_TIME else ''

                        # Email notification to employee for rejection
                        email_subject = f"Taxi Request {status_message} - {request_id}"
                        email_body = f"""<!DOCTYPE html>
                        <html>
<head>
    <meta charset="UTF-8">
    <title>Taxi Request {status_message}</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #dc3545;">
        <h2 style="color: #dc3545; margin-top: 0;">❌ Taxi Request {status_message}</h2>
        <p>Dear <strong>{employee_name}</strong>,</p>
        <p>Your taxi request has been <strong>{status_message.lower()}</strong>.</p>

        <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #dee2e6;">
            <h3 style="color: #495057; margin-top: 0;">📋 Request Details:</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Request ID:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #007bff;">{request_id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Employee:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{employee_name} ({taxi_request[1]})</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Department:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[5]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>From:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[6]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>To:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[7]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Date:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[8]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Time:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[9]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Purpose:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[10]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Passengers:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[11]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Ride Type:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{'Company Taxi' if type_of_ride == 'company_taxi' else 'Own Vehicle'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return Ride:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{'Yes' if returning_ride == 'yes' else 'No'}</td>
                </tr>"""

                        # Add return ride details if it's a two-way ride
                        if returning_ride == 'yes':
                            email_body += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return From:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_from_location if return_from_location else 'Not specified'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return To:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_to_location if return_to_location else 'Not specified'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return Time:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_time if return_time else 'Not specified'}</td>
                </tr>"""

                        email_body += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Status:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #dc3545;">{new_status}</td>
                </tr>
            </table>
        </div>

        <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #dee2e6;">
            <h3 style="color: #495057; margin-top: 0;">📝 HOD Response:</h3>
            <p style="margin: 0; padding: 10px; background-color: #f8f9fa; border-radius: 4px;">{hod_response}</p>
        </div>

        <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px; border: 1px solid #f5c6cb; margin: 15px 0;">
            <p style="margin: 0; color: #721c24;">
                <strong>⚠️ Request Update:</strong>
                Your request has been rejected. Please contact your HOD for more information.
            </p>
        </div>

        <div style="background: #e7f3ff; border: 2px solid #007bff; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
            <h4 style="color: #007bff; margin-top: 0;"><i class="fas fa-tachometer-alt"></i> Access Your Dashboard</h4>
            <p style="margin: 10px 0;">Click the link below to view your request status and manage your taxi requests:</p>
            <a href="{APP_URL}/" style="display: inline-block; background: linear-gradient(45deg, #007bff, #0056b3); color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                <i class="fas fa-sign-in-alt" style="margin-right: 8px;"></i>Go to User Dashboard
            </a>
        </div>

        <p>Thank you for using our Taxi Management System.</p>

        <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
        <p style="font-size: 12px; color: #6c757d; text-align: center; margin: 0;">
            <em>This is an automated message. Please do not reply to this email.</em>
        </p>
    </div>
                        </body>
</html>"""
                        send_email_flask_mail(employee_email, email_subject, email_body, email_type='user_confirmation')

                    # Send WhatsApp notification to user about HOD approval/rejection
                    try:
                        # Create WhatsApp message using the template format
                        hod_name = hod.get('name', 'Your Manager')
                        whatsapp_message = f"""*Taxi Management System*

Hi {employee_name},
Your Manager {hod_name} has updated the status of your query with the following details
*Reference ID:* - {request_id}
*From:* - {taxi_request[6]}
*To:* - {taxi_request[7]}
*Timing:* - {taxi_request[9]}
*Date:* - {taxi_request[8]}"""

                        # Add return journey details only if it's a two-way ride
                        if taxi_request[20] == 'yes':  # returning_ride
                            whatsapp_message += f"""
*Return From:* - {taxi_request[21] if taxi_request[21] else 'Not specified'}
*Return To:* - {taxi_request[22] if taxi_request[22] else 'Not specified'}
*Returning Ride:* - Yes"""

                        whatsapp_message += f"""
*Status:* - {new_status}

Thank You"""

                        # Send WhatsApp notification
                        if employee_phone:
                            send_whatsapp_notification(employee_phone, whatsapp_message)
                        else:
                            print(f"⚠️ No phone number available for WhatsApp notification to {employee_name}")

                    except Exception as whatsapp_error:
                        print(f"❌ Error sending WhatsApp notification: {whatsapp_error}")

                    # If HOD approved, send notification to admin (not to user)
                    if hod_action == 'approve':
                        admin_conn = db_pool.getconn()
                        try:
                            with admin_conn.cursor() as c:
                                # Send notifications only to Nitika Arora (9022761)
                                c.execute('SELECT admin_email, admin_phone, admin_name FROM admins WHERE emp_code = %s AND is_active = TRUE', ('9022761',))
                                admin = c.fetchone()

                                if admin:
                                    admin_email, admin_phone, admin_name = admin

                                    # Email notification to admin
                                    admin_email_subject = f"Taxi Request Approved by HOD - Admin Action Required - {request_id}"
                                    # Extract additional fields from taxi_request
                                    type_of_ride = taxi_request[TYPE_OF_RIDE] if len(taxi_request) > TYPE_OF_RIDE else 'company_taxi'
                                    returning_ride = taxi_request[RETURNING_RIDE] if len(taxi_request) > RETURNING_RIDE else 'no'
                                    return_from_location = taxi_request[RETURN_FROM_LOCATION] if len(taxi_request) > RETURN_FROM_LOCATION else ''
                                    return_to_location = taxi_request[RETURN_TO_LOCATION] if len(taxi_request) > RETURN_TO_LOCATION else ''
                                    return_time = taxi_request[RETURN_TIME] if len(taxi_request) > RETURN_TIME else ''

                                    admin_email_body = f"""<!DOCTYPE html>
                                    <html>
<head>
    <meta charset="UTF-8">
    <title>Taxi Request Approved by HOD - Admin Action Required</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #ffc107;">
        <h2 style="color: #ffc107; margin-top: 0;">🚨 Taxi Request Approved by HOD - Admin Action Required</h2>
                                        <p>A taxi request has been approved by HOD and requires your review.</p>

        <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #dee2e6;">
            <h3 style="color: #495057; margin-top: 0;">📋 Request Details:</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Request ID:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #007bff;">{request_id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Employee:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{employee_name} ({taxi_request[1]})</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Department:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[5]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>From:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[6]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>To:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[7]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Date:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[8]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Time:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[9]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Purpose:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[10]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Passengers:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[11]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Ride Type:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{'Own Vehicle' if type_of_ride == 'own_vehicle' else 'Company Taxi'}</td>
                </tr>"""

                                    # Add vehicle details for own vehicle requests
                                    if type_of_ride == 'own_vehicle':
                                        # Get vehicle details from database
                                        try:
                                            c.execute('''SELECT vehicle_company, vehicle_type, vehicle_number
                                                        FROM taxi_requests WHERE id = %s''', (request_id,))
                                            vehicle_data = c.fetchone()
                                            if vehicle_data:
                                                vehicle_company, vehicle_type, vehicle_number = vehicle_data
                                                admin_email_body += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Vehicle Company:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{vehicle_company or 'Not specified'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Vehicle Type:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{vehicle_type or 'Not specified'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Vehicle Number:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{vehicle_number or 'Not specified'}</td>
                </tr>"""
                                        except Exception as e:
                                            print(f"Error fetching vehicle details: {e}")

                                    # Add return ride information
                                    admin_email_body += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return Ride:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{'Yes' if returning_ride == 'yes' else 'No'}</td>
                </tr>"""

                                    # Add return journey details only if it's a two-way ride
                                    if returning_ride == 'yes':
                                        admin_email_body += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return From:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_from_location or 'Not specified'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return To:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_to_location or 'Not specified'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return Time:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_time or 'Not specified'}</td>
                </tr>"""

                                    admin_email_body += f"""
                <tr>
                    <td style="padding: 8px;"><strong>HOD Response:</strong></td>
                    <td style="padding: 8px;">{hod_response}</td>
                </tr>
            </table>
        </div>

        <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border: 1px solid #ffeaa7; margin: 15px 0;">
            <p style="margin: 0;"><strong>📊 Status:</strong> <span style="color: #856404;">Pending Admin Approval</span></p>
        </div>

        <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; border: 1px solid #bee5eb; margin: 15px 0;">
            <p style="margin: 0; color: #0c5460;"><strong>⚠️ Action Required:</strong> Please review and approve/reject this request.</p>
        </div>

        <div style="background: #d1ecf1; border: 2px solid #17a2b8; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
            <h4 style="color: #0c5460; margin-top: 0;"><i class="fas fa-tachometer-alt"></i> Access Your Dashboard</h4>
            <p style="margin: 10px 0; color: #0c5460;">Click the link below to review and manage taxi requests:</p>
            <a href="{APP_URL}/" style="display: inline-block; background: linear-gradient(45deg, #17a2b8, #138496); color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                <i class="fas fa-user-shield" style="margin-right: 8px;"></i>Go to Admin Dashboard
            </a>
        </div>

        <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
        <p style="font-size: 12px; color: #6c757d; text-align: center; margin: 0;">
            <em>This is an automated message from the Taxi Management System.</em>
        </p>
    </div>
                                    </body>
</html>"""
                                    send_email_flask_mail(admin_email, admin_email_subject, admin_email_body, email_type='admin_approval')

                                    # Send WhatsApp notification to admin
                                    try:
                                        admin_phone = format_phone_number(admin_phone)
                                        if admin_phone:
                                            # Check if it's a two-way ride
                                            if returning_ride == 'yes':
                                                # Two-way ride: include all parameters including return details
                                                admin_parameters = [
                                                    admin_name,                        # {{1}} - Admin name
                                                    employee_name,                    # {{2}} - Employee name
                                                    request_id,                       # {{3}} - Reference ID
                                                    taxi_request[6],                  # {{4}} - From
                                                    taxi_request[7],                  # {{5}} - To
                                                    taxi_request[9],                  # {{6}} - Time
                                                    taxi_request[8],                  # {{7}} - Date
                                                    return_from_location if return_from_location else 'Not specified',  # {{8}} - From (return journey)
                                                    return_to_location if return_to_location else 'Not specified',      # {{9}} - To (return journey)
                                                    return_time if return_time else 'Not specified',                    # {{10}} - Returning Ride time
                                                ]
                                            else:
                                                # One-way ride: use N/A for return details
                                                admin_parameters = [
                                                    admin_name,                        # {{1}} - Admin name
                                                    employee_name,                    # {{2}} - Employee name
                                                    request_id,                       # {{3}} - Reference ID
                                                    taxi_request[6],                  # {{4}} - From
                                                    taxi_request[7],                  # {{5}} - To
                                                    taxi_request[9],                  # {{6}} - Time
                                                    taxi_request[8],                  # {{7}} - Date
                                                    'N/A',                            # {{8}} - From (return journey - N/A for one-way)
                                                    'N/A',                            # {{9}} - To (return journey - N/A for one-way)
                                                    'N/A',                            # {{10}} - Returning Ride time (N/A for one-way)
                                                ]

                                            print(f"📱 Sending WhatsApp notification to admin: {admin_phone}")
                                            send_whatsapp_template(admin_phone, "admin_approval", "en", admin_parameters)
                                        else:
                                            print(f"⚠️ No valid phone number found for admin: {admin_email}")
                                    except Exception as whatsapp_error:
                                        print(f"❌ Error sending WhatsApp notification to admin: {whatsapp_error}")
                        finally:
                            db_pool.putconn(admin_conn)

                        # Send notification to user about HOD approval
                        user_email_subject = f"Taxi Request Approved by HOD - {request_id}"
                        # Extract additional fields from taxi_request for user email
                        type_of_ride = taxi_request[TYPE_OF_RIDE] if len(taxi_request) > TYPE_OF_RIDE else 'company_taxi'
                        returning_ride = taxi_request[RETURNING_RIDE] if len(taxi_request) > RETURNING_RIDE else 'no'
                        return_from_location = taxi_request[RETURN_FROM_LOCATION] if len(taxi_request) > RETURN_FROM_LOCATION else ''
                        return_to_location = taxi_request[RETURN_TO_LOCATION] if len(taxi_request) > RETURN_TO_LOCATION else ''
                        return_time = taxi_request[RETURN_TIME] if len(taxi_request) > RETURN_TIME else ''

                        user_email_body = f"""<!DOCTYPE html>
                        <html>
<head>
    <meta charset="UTF-8">
    <title>Taxi Request Approved by HOD</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #28a745;">
        <h2 style="color: #28a745; margin-top: 0;">✅ Taxi Request Approved by HOD</h2>
        <p>Dear <strong>{employee_name}</strong>,</p>
        <p>Great news! Your taxi request has been <strong>approved by your HOD</strong> and is now pending final admin approval.</p>

        <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #dee2e6;">
            <h3 style="color: #495057; margin-top: 0;">📋 Request Details:</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Request ID:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #007bff;">{request_id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Employee:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{employee_name} ({taxi_request[1]})</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Department:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[5]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>From:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[6]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>To:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[7]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Date:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[8]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Time:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[9]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Purpose:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[10]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Passengers:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[11]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Ride Type:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{'Company Taxi' if type_of_ride == 'company_taxi' else 'Own Vehicle'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return Ride:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{'Yes' if returning_ride == 'yes' else 'No'}</td>
                </tr>"""

                        # Add return ride details if it's a two-way ride
                        if returning_ride == 'yes':
                            user_email_body += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return From:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_from_location if return_from_location else 'Not specified'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return To:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_to_location if return_to_location else 'Not specified'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return Time:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_time if return_time else 'Not specified'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>Status:</strong></td>
                    <td style="padding: 8px; color: #ffc107;">Pending Admin Approval</td>
                </tr>"""
                        else:
                            user_email_body += f"""
                <tr>
                    <td style="padding: 8px;"><strong>Status:</strong></td>
                    <td style="padding: 8px; color: #ffc107;">Pending Admin Approval</td>
                </tr>"""

                        user_email_body += f"""
            </table>
        </div>

        <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #dee2e6;">
            <h3 style="color: #495057; margin-top: 0;">📝 HOD Response:</h3>
            <p style="margin: 0; padding: 10px; background-color: #f8f9fa; border-radius: 4px;">{hod_response}</p>
        </div>

        <div style="background-color: #d4edda; padding: 15px; border-radius: 5px; border: 1px solid #c3e6cb; margin: 15px 0;">
            <p style="margin: 0; color: #155724;">
                <strong>✅ HOD Approval:</strong>
                Your request has been approved by your HOD and is now being reviewed by the admin team.
            </p>
        </div>

        <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border: 1px solid #ffeaa7; margin: 15px 0;">
            <p style="margin: 0; color: #856404;">
                <strong>⏳ Next Step:</strong>
                Your request is now pending admin approval. You will receive another notification once the admin makes a decision.
            </p>
        </div>

        <div style="background: #e7f3ff; border: 2px solid #007bff; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
            <h4 style="color: #007bff; margin-top: 0;"><i class="fas fa-tachometer-alt"></i> Access Your Dashboard</h4>
            <p style="margin: 10px 0;">Click the link below to view your request status and manage your taxi requests:</p>
            <a href="{APP_URL}/" style="display: inline-block; background: linear-gradient(45deg, #007bff, #0056b3); color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                <i class="fas fa-sign-in-alt" style="margin-right: 8px;"></i>Go to User Dashboard
            </a>
        </div>

        <p>Thank you for using our Taxi Management System.</p>

        <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
        <p style="font-size: 12px; color: #6c757d; text-align: center; margin: 0;">
            <em>This is an automated message. Please do not reply to this email.</em>
        </p>
    </div>
                        </body>
</html>"""
                        send_email_flask_mail(employee_email, user_email_subject, user_email_body, email_type='user_confirmation')

                    # Send WhatsApp notification to user about HOD approval/rejection
                    try:
                        # Format user phone number for WhatsApp
                        user_phone = format_phone_number(employee_phone)
                        if user_phone:
                            # Extract additional fields from taxi_request for WhatsApp template
                            type_of_ride = taxi_request[22] if len(taxi_request) > 22 else 'company_taxi'  # type_of_ride
                            returning_ride = taxi_request[26] if len(taxi_request) > 26 else 'no'  # returning_ride
                            return_from_location = taxi_request[27] if len(taxi_request) > 27 else ''  # return_from_location
                            return_to_location = taxi_request[28] if len(taxi_request) > 28 else ''  # return_to_location
                            return_time = taxi_request[29] if len(taxi_request) > 29 else ''  # return_time

                            hod_name = hod.get('hod_name', 'Your Manager')

                            # Use the user_hod_approval_reject template
                            template_name = "user_hod_approval_reject"
                            parameters = [
                                employee_name,                    # {{1}} - Employee name
                                hod_name,                        # {{2}} - HOD name
                                request_id,                      # {{3}} - Reference ID
                                taxi_request[6],                 # {{4}} - From
                                taxi_request[7],                 # {{5}} - To
                                taxi_request[9],                 # {{6}} - Time
                                taxi_request[8],                 # {{7}} - Date
                                return_from_location if return_from_location else 'N/A',  # {{8}} - From (return journey)
                                return_to_location if return_to_location else 'N/A',      # {{9}} - To (return journey)
                                return_time if return_time else 'N/A',                    # {{10}} - Returning Ride time
                                new_status                       # {{11}} - Status
                            ]

                            print(f"📱 Sending WhatsApp notification to user: {user_phone}")
                            send_whatsapp_template(user_phone, template_name, "en", parameters)
                        else:
                            print(f"⚠️ No valid phone number found for user: {employee_name}")

                    except Exception as whatsapp_error:
                        print(f"❌ Error sending WhatsApp notification: {whatsapp_error}")

                    flash(f'Request {status_message.lower()} successfully', 'success')
                    return redirect(url_for('hod_dashboard'))

                except Exception as e:
                    print(f"HOD Response Error: {str(e)}")
                    flash(f'Error processing request: {str(e)}', 'error')
                    budget_info = get_hod_budget_info_by_email(hod['hod_email'])
                    return render_template('hod_response.html', request=taxi_request, taxi_reason=taxi_reason, budget_info=budget_info)

            # Get HOD-specific budget information for template
            budget_info = get_hod_budget_info_by_email(hod['hod_email'])
            return render_template('hod_response.html', request=taxi_request, taxi_reason=taxi_reason, budget_info=budget_info)
    finally:
        db_pool.putconn(conn)

@app.route('/admin_response/<request_id>', methods=['GET', 'POST'])
def admin_response(request_id):
    if 'admin' not in session or not session['admin'].get('authenticated'):
        flash('Please login as admin first', 'error')
        return redirect(url_for('admin_login'))

    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            # Get basic request data first
            c.execute('''SELECT id, emp_code, employee_name, employee_email, employee_phone, department,
                               from_location, to_location, travel_date, travel_time, purpose, passengers,
                               status, hod_response, admin_response, taxi_details, type_of_ride,
                               vehicle_company, vehicle_type, vehicle_number, returning_ride,
                               return_from_location, return_to_location, return_time
                        FROM taxi_requests WHERE id = %s''', (request_id,))
            basic_request = c.fetchone()

            # Get taxi reason from taxi_reason table
            taxi_reason = None
            if basic_request:
                c.execute('''SELECT reason FROM taxi_reason WHERE reference_id = %s''', (request_id,))
                reason_result = c.fetchone()
                taxi_reason = reason_result[0] if reason_result else None

            if basic_request:
                # Build complete request data with safe timestamp handling
                req_list = list(basic_request)

                # Add placeholder timestamp fields
                # Current list has 24 elements (indices 0-23), so we add 4 more (indices 24-27)
                req_list.extend(['N/A', 'N/A', 'N/A', 'N/A'])  # hod_approval_date, submission_date, admin_response_date, created_at

                # Try to get actual timestamp values safely
                try:
                    c.execute('''SELECT
                                   COALESCE(TO_CHAR(hod_approval_date, 'YYYY-MM-DD HH24:MI'), 'N/A'),
                                   COALESCE(TO_CHAR(submission_date, 'YYYY-MM-DD HH24:MI'), 'N/A'),
                                   COALESCE(TO_CHAR(admin_response_date, 'YYYY-MM-DD HH24:MI'), 'N/A'),
                                   COALESCE(TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI'), 'N/A')
                               FROM taxi_requests WHERE id = %s''', (request_id,))
                    timestamps = c.fetchone()
                    if timestamps:
                        req_list[24] = timestamps[0]  # hod_approval_date
                        req_list[25] = timestamps[1]  # submission_date

                        req_list[26] = timestamps[2]  # admin_response_date
                        req_list[27] = timestamps[3]  # created_at
                except Exception as timestamp_error:
                    print(f"Warning: Could not get timestamps for admin response request {request_id}: {timestamp_error}")

                taxi_request = tuple(req_list)
            else:
                taxi_request = None

            if not taxi_request:
                flash('Request not found', 'error')
                return redirect(url_for('admin_dashboard'))

            if request.method == 'POST':
                status = request.form.get('status')
                admin_response = request.form.get('admin_response')
                taxi_details = request.form.get('taxi_details')

                if not all([status, admin_response]):
                    flash('Please fill in all required fields', 'error')
                    return render_template('admin_response.html', request=taxi_request, taxi_reason=taxi_reason)

                # Update request
                c.execute('''UPDATE taxi_requests
                            SET status = %s, admin_response = %s, taxi_details = %s, admin_response_date = %s
                            WHERE id = %s''',
                         (status, admin_response, taxi_details, datetime.now(), request_id))
                conn.commit()

                # Note: 24-hour reminders are now handled by the overdue reminder scheduler
                # No need to schedule individual reminders here

                # Send notification to employee
                employee_email = taxi_request[3]
                employee_phone = taxi_request[4]
                employee_name = taxi_request[2]

                print(f"📧 Sending admin response email to {employee_name} ({employee_email})")
                print(f"📧 Status: {status}, Response: {admin_response[:50]}...")

                # Extract additional fields from taxi_request for admin email
                # Note: The query returns fields in different order than the constants expect
                type_of_ride = taxi_request[16] if len(taxi_request) > 16 else 'company_taxi'  # type_of_ride
                returning_ride = taxi_request[20] if len(taxi_request) > 20 else 'no'  # returning_ride
                return_from_location = taxi_request[21] if len(taxi_request) > 21 else ''  # return_from_location
                return_to_location = taxi_request[22] if len(taxi_request) > 22 else ''  # return_to_location
                return_time = taxi_request[23] if len(taxi_request) > 23 else ''  # return_time

                # Debug: Print return ride details
                print(f"🔍 Admin Email Debug - Return Ride Details:")
                print(f"   Taxi Request Length: {len(taxi_request)}")
                print(f"   Returning Ride (index 20): {returning_ride}")
                print(f"   Return From (index 21): {return_from_location}")
                print(f"   Return To (index 22): {return_to_location}")
                print(f"   Return Time (index 23): {return_time}")
                print(f"   Type of Ride (index 16): {type_of_ride}")

                # Email notification to employee
                email_subject = f"Taxi Request Update - {request_id}"
                email_body = f"""<!DOCTYPE html>
                <html>
<head>
    <meta charset="UTF-8">
    <title>Taxi Request Update</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #17a2b8;">
        <h2 style="color: #17a2b8; margin-top: 0;">📋 Taxi Request Update</h2>
        <p>Dear <strong>{employee_name}</strong>,</p>
        <p>Your taxi request has been reviewed and updated by the admin.</p>

        <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #dee2e6;">
            <h3 style="color: #495057; margin-top: 0;">📋 Request Details:</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Request ID:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #007bff;">{request_id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Employee:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{employee_name} ({taxi_request[1]})</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Department:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[5]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>From:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[6]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>To:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[7]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Date:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[8]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Time:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[9]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Purpose:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[10]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Passengers:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{taxi_request[11]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Ride Type:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{'Company Taxi' if type_of_ride == 'company_taxi' else 'Own Vehicle'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return Ride:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{'Yes' if returning_ride == 'yes' else 'No'}</td>
                </tr>"""

                # Add return ride details if it's a two-way ride
                if returning_ride == 'yes':
                    email_body += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return From:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_from_location if return_from_location else 'Not specified'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return To:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_to_location if return_to_location else 'Not specified'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Return Time:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{return_time if return_time else 'Not specified'}</td>
                </tr>"""

                email_body += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6;"><strong>Status:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #17a2b8;">{status}</td>
                </tr>"""

                # Add taxi details if provided
                if taxi_details:
                    email_body += f"""
                <tr>
                    <td style="padding: 8px;"><strong>Taxi Details:</strong></td>
                    <td style="padding: 8px;">{taxi_details}</td>
                </tr>"""
                else:
                    email_body += f"""
                <tr>
                    <td style="padding: 8px;"><strong>Admin Response:</strong></td>
                    <td style="padding: 8px;">{admin_response}</td>
                </tr>"""

                email_body += f"""
            </table>
        </div>

        <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; margin: 15px 0; border: 1px solid #dee2e6;">
            <h3 style="color: #495057; margin-top: 0;">📝 Admin Response:</h3>
            <p style="margin: 0; padding: 10px; background-color: #f8f9fa; border-radius: 4px;">{admin_response}</p>
        </div>

        <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; border: 1px solid #bee5eb; margin: 15px 0;">
            <p style="margin: 0; color: #0c5460;"><strong>ℹ️Please Note:</strong> the start and end meter readings as this is required for feedback.</p>
        </div>

        <div style="background: #e7f3ff; border: 2px solid #007bff; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
            <h4 style="color: #007bff; margin-top: 0;"><i class="fas fa-tachometer-alt"></i> Access Your Dashboard</h4>
            <p style="margin: 10px 0;">Click the link below to review and manage taxi requests:</p>
            <a href="{APP_URL}/" style="display: inline-block; background: linear-gradient(45deg, #007bff, #0056b3); color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                <i class="fas fa-sign-in-alt" style="margin-right: 8px;"></i>Go to User Dashboard
            </a>
        </div>

                    <p>Thank you for using our Taxi Management System.</p>

        <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">
        <p style="font-size: 12px; color: #6c757d; text-align: center; margin: 0;">
            <em>This is an automated message. Please do not reply to this email.</em>
        </p>
    </div>
                </body>
</html>"""
                email_sent = send_email_flask_mail(employee_email, email_subject, email_body, email_type='user_confirmation')

                # Send WhatsApp notification to user
                try:
                    user_phone = format_phone_number(employee_phone)
                    if user_phone:
                        # Get admin name from session
                        admin_name = session['admin'].get('admin_name', 'Admin')

                        # Check if it's a two-way ride
                        if returning_ride == 'yes':
                            # Two-way ride: include all parameters including return details
                            user_parameters = [
                                employee_name,                    # {{1}} - Employee name
                                admin_name,                       # {{2}} - Admin name
                                request_id,                       # {{3}} - Reference ID
                                taxi_request[6],                  # {{4}} - From
                                taxi_request[7],                  # {{5}} - To
                                taxi_request[9],                  # {{6}} - Time
                                taxi_request[8],                  # {{7}} - Date
                                return_from_location if return_from_location else 'Not specified',  # {{8}} - From (return journey)
                                return_to_location if return_to_location else 'Not specified',      # {{9}} - To (return journey)
                                return_time if return_time else 'Not specified',                    # {{10}} - Returning Ride time
                                status,                           # {{11}} - Status
                                taxi_details if taxi_details else 'Not provided'  # {{12}} - Taxi Details
                            ]
                        else:
                            # One-way ride: use N/A for return details
                            user_parameters = [
                                employee_name,                    # {{1}} - Employee name
                                admin_name,                       # {{2}} - Admin name
                                request_id,                       # {{3}} - Reference ID
                                taxi_request[6],                  # {{4}} - From
                                taxi_request[7],                  # {{5}} - To
                                taxi_request[9],                  # {{6}} - Time
                                taxi_request[8],                  # {{7}} - Date
                                'N/A',                            # {{8}} - From (return journey - N/A for one-way)
                                'N/A',                            # {{9}} - To (return journey - N/A for one-way)
                                'N/A',                            # {{10}} - Returning Ride time (N/A for one-way)
                                status,                           # {{11}} - Status
                                taxi_details if taxi_details else 'Not provided'  # {{12}} - Taxi Details
                            ]

                        print(f"📱 Sending WhatsApp notification to user: {user_phone}")
                        send_whatsapp_template(user_phone, "user_admin_approval_reject", "en", user_parameters)
                    else:
                        print(f"⚠️ No valid phone number found for user: {employee_name}")
                except Exception as whatsapp_error:
                    print(f"❌ Error sending WhatsApp notification to user: {whatsapp_error}")

                if email_sent:
                    print(f"✅ Email sent successfully to {employee_email}")
                    flash(f'Response submitted successfully! Email notification sent to {employee_name}.', 'success')
                else:
                    print(f"❌ Failed to send email to {employee_email}")
                    flash(f'Response submitted successfully, but email notification failed to send to {employee_name}.', 'warning')
                return redirect(url_for('admin_dashboard'))

            return render_template('admin_response.html', request=taxi_request, taxi_reason=taxi_reason)
    finally:
        db_pool.putconn(conn)

@app.route('/hod_budget')
def hod_budget():
    """HOD Budget Management Page"""
    if 'admin' not in session or not session['admin'].get('authenticated'):
        flash('Please login as admin first', 'error')
        return redirect(url_for('admin_login'))

    try:
        # Get all HOD budgets
        hod_budgets = get_all_hod_budgets()
        current_year = datetime.now().year

        # Debug: Check database table structure
        conn = db_pool.getconn()
        try:
            with conn.cursor() as c:
                c.execute("""
                    SELECT column_name, data_type, ordinal_position
                    FROM information_schema.columns
                    WHERE table_name = 'hod_budget'
                    ORDER BY ordinal_position
                """)
                columns = c.fetchall()
                print(f"🔍 HOD Budget Table Structure:")
                for col in columns:
                    print(f"  {col[2]}: {col[0]} ({col[1]})")
        except Exception as e:
            print(f"❌ Error checking table structure: {str(e)}")
        finally:
            db_pool.putconn(conn)

        # Debug: Print the first few HOD budgets to check data structure
        print(f"🔍 HOD Budgets Data Structure:")
        for i, hod in enumerate(hod_budgets[:3]):  # Print first 3 for debugging
            print(f"  HOD {i+1}: {hod}")

        return render_template('hod_budget.html',
                             hod_budgets=hod_budgets,
                             current_year=current_year)
    except Exception as e:
        print(f"❌ Error loading HOD budget page: {str(e)}")
        flash('Error loading HOD budget information', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/update_hod_budget', methods=['POST'])
def update_hod_budget():
    """Update HOD budget from admin page"""
    if 'admin' not in session or not session['admin'].get('authenticated'):
        return jsonify({'success': False, 'error': 'Not authenticated'})

    try:
        hod_emp_code = request.form.get('hod_emp_code')
        total_budget = float(request.form.get('total_budget', 0))
        used_budget = float(request.form.get('used_budget', 0))

        if not hod_emp_code or total_budget < 0 or used_budget < 0:
            return jsonify({'success': False, 'error': 'Invalid data provided'})

        # Allow negative remaining budget (used budget can exceed total budget)

        conn = db_pool.getconn()
        try:
            with conn.cursor() as c:
                current_year = datetime.now().year

                # Get current HOD budget info
                c.execute('''SELECT hod_name FROM hod_budget
                            WHERE hod_emp_code = %s AND budget_year = %s''', (hod_emp_code, current_year))
                result = c.fetchone()

                if not result:
                    return jsonify({'success': False, 'error': 'HOD budget not found'})

                hod_name = result[0]

                # Calculate remaining budget
                remaining_budget = total_budget - used_budget

                # Update the budget
                c.execute('''UPDATE hod_budget
                            SET total_budget = %s, used_budget = %s, remaining_budget = %s, updated_at = CURRENT_TIMESTAMP
                            WHERE hod_emp_code = %s AND budget_year = %s''',
                            (total_budget, used_budget, remaining_budget, hod_emp_code, current_year))

                conn.commit()

                return jsonify({
                    'success': True,
                    'hod_name': hod_name,
                    'total_budget': total_budget,
                    'used_budget': used_budget,
                    'remaining_budget': remaining_budget
                })

        finally:
            db_pool.putconn(conn)

    except Exception as e:
        print(f"❌ Error updating HOD budget: {str(e)}")
        return jsonify({'success': False, 'error': 'Database error occurred'})

@app.route('/send_feedback_reminders', methods=['POST'])
def send_feedback_reminders():
    """Admin route to manually send feedback reminders"""
    if 'admin' not in session or not session['admin'].get('authenticated'):
        flash('Please login as admin first', 'error')
        return redirect(url_for('admin_login'))

    try:
        # Call the feedback reminder function
        check_and_send_feedback_reminders()
        flash('Feedback reminders sent successfully!', 'success')
    except Exception as e:
        print(f"❌ Error sending feedback reminders: {str(e)}")
        flash(f'Error sending feedback reminders: {str(e)}', 'error')

    return redirect(url_for('admin_dashboard'))

@app.route('/update_budget', methods=['POST'])
def update_budget_admin():
    """Update budget from admin dashboard"""
    if 'admin' not in session or not session['admin'].get('authenticated'):
        flash('Please login as admin first', 'error')
        return redirect(url_for('admin_login'))

    try:
        total_budget = float(request.form.get('total_budget', 0))
        used_budget = float(request.form.get('used_budget', 0))
        current_year = datetime.now().year

        # Validate budget values
        if total_budget < 0 or used_budget < 0:
            flash('Budget amounts cannot be negative.', 'error')
            return redirect(url_for('admin_dashboard'))

        # Allow negative remaining budget (used budget can exceed total budget)
        remaining_budget = total_budget - used_budget

        conn = db_pool.getconn()
        try:
            with conn.cursor() as c:
                # Check if budget entry exists
                c.execute('''SELECT id FROM budget_management
                            WHERE budget_year = %s''', (current_year,))
                result = c.fetchone()

                if result:
                    # Update existing budget
                    c.execute('''UPDATE budget_management
                                SET total_budget = %s, used_budget = %s, remaining_budget = %s
                                WHERE budget_year = %s''', (total_budget, used_budget, remaining_budget, current_year))
                else:
                    # Create new budget entry
                    c.execute('''INSERT INTO budget_management (total_budget, used_budget, remaining_budget, budget_year)
                                VALUES (%s, %s, %s, %s)''', (total_budget, used_budget, remaining_budget, current_year))

                conn.commit()
                flash(f'Budget updated successfully! Total: ₹{total_budget:,.2f}, Used: ₹{used_budget:,.2f}, Remaining: ₹{remaining_budget:,.2f}', 'success')
        finally:
            db_pool.putconn(conn)

    except ValueError:
        flash('Invalid budget amount. Please enter valid numbers.', 'error')
    except Exception as e:
        print(f"❌ Error updating budget: {str(e)}")
        flash('Error updating budget. Please try again.', 'error')

    return redirect(url_for('admin_dashboard'))


@app.route('/logout')
def logout():
    # Check which session was active before clearing
    was_hod = 'hod' in session and session['hod'].get('authenticated', False)
    was_admin = 'admin' in session and session['admin'].get('authenticated', False)
    was_user = 'user' in session and session['user'].get('authenticated', False)

    # Clear all sessions and flash messages
    session.pop('user', None)
    session.pop('admin', None)
    session.pop('hod', None)

    # Clear any existing flash messages before setting new one
    try:
        get_flashed_messages(with_categories=True)
        session.pop('_flashes', None)
    except:
        pass

    flash('Logged out successfully', 'success')

    # Redirect to appropriate login page based on what was active
    if was_hod:
        return redirect(url_for('hod_login'))
    elif was_admin:
        return redirect(url_for('admin_login'))
    else:
        return redirect(url_for('login'))

@app.route('/edit_request/<request_id>', methods=['GET', 'POST'])
def edit_request(request_id):
    """Edit taxi request when admin requests more information"""
    if 'user' not in session or not session['user'].get('authenticated'):
        flash('Please login first', 'error')
        return redirect(url_for('login'))

    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            # Get basic request data first
            c.execute('''SELECT id, emp_code, employee_name, employee_email, employee_phone, department,
                               from_location, to_location, travel_date, travel_time, purpose, passengers,
                               status, hod_response, admin_response, taxi_details, type_of_ride,
                               returning_ride, return_from_location, return_to_location, return_time
                        FROM taxi_requests WHERE id = %s''', (request_id,))
            basic_request = c.fetchone()

            if basic_request:
                # Build complete request data with safe timestamp handling
                req_list = list(basic_request)

                # Add placeholder timestamp fields
                # Current list has 21 elements (indices 0-20), so we add 4 more (indices 21-24)
                req_list.extend(['N/A', 'N/A', 'N/A', 'N/A'])  # hod_approval_date, submission_date, admin_response_date, created_at

                # Try to get actual timestamp values safely
                try:
                    c.execute('''SELECT
                                   COALESCE(hod_approval_date::text, 'N/A'),
                                   COALESCE(submission_date::text, 'N/A'),
                                   COALESCE(admin_response_date::text, 'N/A'),
                                   COALESCE(created_at::text, 'N/A')
                               FROM taxi_requests WHERE id = %s''', (request_id,))
                    timestamps = c.fetchone()
                    if timestamps:
                        req_list[21] = timestamps[0]  # hod_approval_date
                        req_list[22] = timestamps[1]  # submission_date
                        req_list[23] = timestamps[2]  # admin_response_date
                        req_list[24] = timestamps[3]  # created_at
                except Exception as timestamp_error:
                    print(f"Warning: Could not get timestamps for edit request {request_id}: {timestamp_error}")

                taxi_request = tuple(req_list)
            else:
                taxi_request = None

            if not taxi_request:
                flash('Request not found', 'error')
                return redirect(url_for('user_dashboard'))

            # Check if user owns this request
            if taxi_request[1] != session['user']['emp_code']:
                flash('Access denied: You can only edit your own requests', 'error')
                return redirect(url_for('user_dashboard'))

            # Check if status allows editing (Only "Pending" with admin response containing "more information" allows editing)
            admin_response = taxi_request[13] or ''
            can_edit = (
                taxi_request[12] == 'Pending' and 'more information' in admin_response.lower()
            )

            if not can_edit:
                flash('This request cannot be edited. Only pending requests with admin response requesting more information can be edited.', 'error')
                return redirect(url_for('user_dashboard'))

            if request.method == 'POST':
                # Get form data
                from_location = request.form.get('from_location')
                to_location = request.form.get('to_location')
                travel_date = request.form.get('travel_date')
                travel_time = request.form.get('travel_time')
                purpose = request.form.get('purpose')
                passengers = request.form.get('passengers', 1)

                if not all([from_location, to_location, travel_date, travel_time, purpose]):
                    flash('Please fill in all required fields', 'error')
                    return render_template('edit_request.html', request=taxi_request)

                # Update request
                c.execute('''UPDATE taxi_requests
                            SET from_location = %s, to_location = %s, travel_date = %s,
                                travel_time = %s, purpose = %s, passengers = %s,
                                status = %s, admin_response = %s, admin_response_date = %s
                            WHERE id = %s''',
                         (from_location, to_location, travel_date, travel_time, purpose,
                          passengers, 'Pending', 'Request updated by user', datetime.now(), request_id))
                conn.commit()

                # Send notification to admins about the update
                admin_conn = db_pool.getconn()
                try:
                    with admin_conn.cursor() as c:
                        # Send notifications only to Nitika Arora (9022761)
                        c.execute('SELECT admin_email FROM admins WHERE emp_code = %s AND is_active = TRUE', ('9022761',))
                        admin = c.fetchone()

                        if admin:
                            admin_email = admin[0]

                            # Email notification to admin
                            admin_email_subject = f"Taxi Request Updated - {request_id}"
                            admin_email_body = f"""
                            <html>
                            <body style="font-family: Arial, sans-serif;">
                                <h2>Taxi Request Updated by User</h2>
                                <p><strong>Request ID:</strong> {request_id}</p>
                                <p><strong>Employee:</strong> {session['user']['employee_name']} ({session['user']['emp_code']})</p>
                                <p><strong>Updated Information:</strong></p>
                                <ul>
                                    <li><strong>From:</strong> {from_location}</li>
                                    <li><strong>To:</strong> {to_location}</li>
                                    <li><strong>Date:</strong> {travel_date}</li>
                                    <li><strong>Time:</strong> {travel_time}</li>
                                    <li><strong>Purpose:</strong> {purpose}</li>
                                    <li><strong>Passengers:</strong> {passengers}</li>
                                </ul>
                                <p><strong>Status:</strong> Updated to Pending</p>
                                <p>Please review the updated request.</p>
                            </body>
                            </html>
                            """
                            send_email_flask_mail(admin_email, admin_email_subject, admin_email_body, email_type='admin_approval')

                        # Send confirmation email to user
                        user_email_subject = f"Taxi Request Updated - {request_id}"
                        user_email_body = f"""
                        <html>
                        <body style="font-family: Arial, sans-serif;">
                            <h2>Taxi Request Updated Successfully</h2>
                            <p>Dear {session['user']['employee_name']},</p>
                            <p>Your taxi request has been updated and is now pending review again.</p>
                            <p><strong>Updated Request Details:</strong></p>
                            <ul>
                                <li><strong>Request ID:</strong> {request_id}</li>
                                <li><strong>From:</strong> {from_location}</li>
                                <li><strong>To:</strong> {to_location}</li>
                                <li><strong>Date:</strong> {travel_date}</li>
                                <li><strong>Time:</strong> {travel_time}</li>
                                <li><strong>Purpose:</strong> {purpose}</li>
                                <li><strong>Passengers:</strong> {passengers}</li>
                            </ul>
                            <p><strong>Status:</strong> Pending Review</p>
                            <p>You will receive an update once your request has been reviewed by the admin.</p>

                            <div style="background: #e7f3ff; border: 2px solid #007bff; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                                <h4 style="color: #007bff; margin-top: 0;"><i class="fas fa-tachometer-alt"></i> Access Your Dashboard</h4>
                                <p style="margin: 10px 0;">Click the link below to review and manage taxi requests:</p>
                                <a href="{APP_URL}/" style="display: inline-block; background: linear-gradient(45deg, #007bff, #0056b3); color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 0;">
                                    <i class="fas fa-sign-in-alt" style="margin-right: 8px;"></i>Go to User Dashboard
                                </a>
                            </div>

                            <p>Thank you for using our Taxi Management System.</p>
                            <br>
                            <p><em>This is an automated message. Please do not reply to this email.</em></p>
                        </body>
                        </html>
                        """
                        send_email_flask_mail(session['user']['employee_email'], user_email_subject, user_email_body, email_type='user_confirmation')

                finally:
                    db_pool.putconn(admin_conn)

                flash('Request updated successfully! The admin has been notified.', 'success')
                return redirect(url_for('user_dashboard'))

            return render_template('edit_request.html', request=taxi_request)
    finally:
        db_pool.putconn(conn)

@app.route('/api/get_employee_details')
def get_employee_details():
    emp_code = request.args.get('emp_code')
    if not emp_code:
        return jsonify({'success': False, 'error': 'Employee code required'})

    result = verify_sap_credentials(emp_code, '')
    if result['success']:
        return jsonify({
            'success': True,
            'employee_name': result['employee_name'],
            'employee_email': result['employee_email'],
            'employee_phone': result['employee_phone'],
            'department': result['department']
        })
    else:
        return jsonify({'success': False, 'error': result.get('error', 'Employee not found')})

@app.route('/feedback/<request_id>')
def feedback_form(request_id):
    """Display feedback form for a specific taxi request"""
    if 'user' not in session or not session['user'].get('authenticated'):
        flash('Please login first', 'error')
        return redirect(url_for('login'))

    user = session['user']

    # Verify that the request belongs to the current user and is approved
    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            c.execute('''SELECT id, status, emp_code FROM taxi_requests
                        WHERE id = %s AND emp_code = %s''', (request_id, user['emp_code']))
            request_data = c.fetchone()

            if not request_data:
                flash('Request not found or access denied', 'error')
                return redirect(url_for('user_dashboard'))

            # Check if request is approved and is a company taxi request
            if request_data[1] != 'Approved':
                flash('Feedback can only be submitted for approved requests', 'error')
                return redirect(url_for('user_dashboard'))

            # Get request details to check if it's a company taxi request
            c.execute('''SELECT type_of_ride FROM taxi_requests WHERE id = %s''', (request_id,))
            request_details = c.fetchone()

            if not request_details or request_details[0] != 'company_taxi':
                flash('Feedback can only be submitted for company taxi requests', 'error')
                return redirect(url_for('user_dashboard'))

            # Check if feedback already exists
            c.execute('SELECT id FROM taxi_feedback WHERE request_id = %s', (request_id,))
            existing_feedback = c.fetchone()

            if existing_feedback:
                flash('Feedback has already been submitted for this request', 'error')
                return redirect(url_for('user_dashboard'))

            return render_template('feedback.html', request_id=request_id)

    finally:
        db_pool.putconn(conn)

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    """Handle feedback form submission"""
    if 'user' not in session or not session['user'].get('authenticated'):
        return jsonify({'success': False, 'message': 'Please login first'})

    user = session['user']
    request_id = request.form.get('request_id')
    rating = request.form.get('rating')
    comment = request.form.get('comment', '')
    start_meter = request.form.get('start_meter', '')
    end_meter = request.form.get('end_meter', '')

    # Validate required fields
    if not request_id or not rating:
        return jsonify({'success': False, 'message': 'Missing required fields'})

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            return jsonify({'success': False, 'message': 'Invalid rating'})
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid rating format'})

    # Validate comment for poor rating
    if rating == 1 and not comment.strip():
        return jsonify({'success': False, 'message': 'Comment is required for poor rating'})

    # Calculate total distance if meter readings provided
    total_distance = None
    if start_meter and end_meter:
        try:
            start = float(start_meter)
            end = float(end_meter)
            if end >= start:
                total_distance = end - start
        except ValueError:
            pass

    conn = db_pool.getconn()
    try:
        with conn.cursor() as c:
            # Verify request belongs to user and is approved
            c.execute('''SELECT id, status, emp_code FROM taxi_requests
                        WHERE id = %s AND emp_code = %s''', (request_id, user['emp_code']))
            request_data = c.fetchone()

            if not request_data:
                return jsonify({'success': False, 'message': 'Request not found or access denied'})

            if request_data[1] != 'Approved':
                return jsonify({'success': False, 'message': 'Feedback can only be submitted for approved requests'})

            # Get request details to check if it's a company taxi request
            c.execute('''SELECT type_of_ride FROM taxi_requests WHERE id = %s''', (request_id,))
            request_details = c.fetchone()

            if not request_details or request_details[0] != 'company_taxi':
                return jsonify({'success': False, 'message': 'Feedback can only be submitted for company taxi requests'})

            # Check if feedback already exists
            c.execute('SELECT id FROM taxi_feedback WHERE request_id = %s', (request_id,))
            existing_feedback = c.fetchone()

            if existing_feedback:
                return jsonify({'success': False, 'message': 'Feedback has already been submitted for this request'})

            # Insert feedback
            c.execute('''INSERT INTO taxi_feedback
                        (request_id, emp_code, employee_name, employee_email, rating, comment,
                         start_meter, end_meter, total_distance)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                     (request_id, user['emp_code'], user['employee_name'], user['employee_email'],
                      rating, comment.strip() if comment else None,
                      float(start_meter) if start_meter else None,
                      float(end_meter) if end_meter else None,
                      total_distance))

            conn.commit()

            print(f"✅ Feedback submitted for request {request_id} by {user['employee_name']} (Rating: {rating})")

            return jsonify({'success': True, 'message': 'Feedback submitted successfully'})

    except Exception as e:
        print(f"❌ Error submitting feedback: {str(e)}")
        return jsonify({'success': False, 'message': 'Error submitting feedback'})

    finally:
        db_pool.putconn(conn)

@app.route('/admin_feedback')
def admin_feedback():
    """Display all user feedback for admin review with filtering"""
    if 'admin' not in session or not session['admin'].get('authenticated'):
        flash('Admin access required', 'error')
        return redirect(url_for('admin_login'))

    admin = session['admin']

    # Get filter parameters
    rating_filter = request.args.get('rating', '').strip()
    employee_filter = request.args.get('employee', '').strip()
    date_range_filter = request.args.get('date_range', '').strip()

    conn = db_pool.getconn()

    try:
        with conn.cursor() as c:
            # Build the base query
            base_query = '''
                SELECT
                    tf.id,
                    tf.request_id,
                    tf.emp_code,
                    tf.employee_name,
                    tf.employee_email,
                    tf.rating,
                    tf.comment,
                    tf.start_meter,
                    tf.end_meter,
                    tf.total_distance,
                    tf.feedback_date,
                    tr.department,
                    tr.from_location,
                    tr.to_location,
                    tr.travel_date,
                    tr.travel_time,
                    tr.purpose
                FROM taxi_feedback tf
                LEFT JOIN taxi_requests tr ON tf.request_id = tr.id
            '''

            # Build WHERE conditions
            where_conditions = []
            params = []

            # Rating filter
            if rating_filter:
                where_conditions.append('tf.rating = %s')
                params.append(int(rating_filter))

            # Employee filter (search by name, email, or emp_code)
            if employee_filter:
                where_conditions.append('''
                    (tf.employee_name ILIKE %s OR
                     tf.employee_email ILIKE %s OR
                     tf.emp_code ILIKE %s)
                ''')
                search_term = f'%{employee_filter}%'
                params.extend([search_term, search_term, search_term])

            # Date range filter
            if date_range_filter:
                if date_range_filter == 'today':
                    where_conditions.append('DATE(tf.feedback_date) = CURRENT_DATE')
                elif date_range_filter == 'week':
                    where_conditions.append('tf.feedback_date >= NOW() - INTERVAL \'7 days\'')
                elif date_range_filter == 'month':
                    where_conditions.append('tf.feedback_date >= NOW() - INTERVAL \'30 days\'')

            # Combine query with filters
            if where_conditions:
                query = base_query + ' WHERE ' + ' AND '.join(where_conditions) + ' ORDER BY tf.feedback_date DESC'
            else:
                query = base_query + ' ORDER BY tf.feedback_date DESC'

            print(f"🔍 Admin Feedback Query: {query}")
            print(f"📊 Parameters: {params}")

            # Execute the filtered query
            c.execute(query, params)
            feedbacks = c.fetchall()

            # Get feedback statistics (always get total stats, not filtered)
            c.execute('''
                SELECT
                    COUNT(*) as total_feedback,
                    AVG(rating) as avg_rating,
                    COUNT(CASE WHEN rating = 5 THEN 1 END) as excellent_count,
                    COUNT(CASE WHEN rating = 4 THEN 1 END) as very_good_count,
                    COUNT(CASE WHEN rating = 3 THEN 1 END) as good_count,
                    COUNT(CASE WHEN rating = 2 THEN 1 END) as fair_count,
                    COUNT(CASE WHEN rating = 1 THEN 1 END) as poor_count
                FROM taxi_feedback
            ''')
            stats = c.fetchone()

            # Get recent feedback (last 7 days)
            c.execute('''
                SELECT COUNT(*)
                FROM taxi_feedback
                WHERE feedback_date >= NOW() - INTERVAL '7 days'
            ''')
            recent_count = c.fetchone()[0]

            print(f"✅ Found {len(feedbacks)} feedback records")

    except Exception as e:
        print(f"❌ Error fetching admin feedback data: {e}")
        traceback.print_exc()
        flash('Error loading feedback data', 'error')
        feedbacks = []
        stats = (0, 0, 0, 0, 0, 0, 0)
        recent_count = 0

    finally:
        db_pool.putconn(conn)

    return render_template('admin_feedback.html',
                         feedbacks=feedbacks,
                         stats=stats,
                         recent_count=recent_count,
                         admin=admin,
                         current_filters={
                             'rating': rating_filter,
                             'employee': employee_filter,
                             'date_range': date_range_filter
                         })

@app.route('/admin_own_vehicle')
def admin_own_vehicle():
    """Display all own vehicle requests for admin review with filtering"""
    if 'admin' not in session or not session['admin'].get('authenticated'):
        flash('Admin access required', 'error')
        return redirect(url_for('admin_login'))

    admin = session['admin']

    # Get filter parameters
    employee_filter = request.args.get('employee', '').strip()
    date_range_filter = request.args.get('date_range', '').strip()

    conn = db_pool.getconn()

    try:
        with conn.cursor() as c:
            # Build the base query for own vehicle requests
            base_query = '''
                SELECT
                    tr.id,
                    tr.emp_code,
                    tr.employee_name,
                    tr.employee_email,
                    tr.department,
                    tr.from_location,
                    tr.to_location,
                    tr.travel_date,
                    tr.travel_time,
                    tr.purpose,
                    tr.vehicle_company,
                    tr.vehicle_type,
                    tr.vehicle_number,
                    tr.status,
                    tr.created_at
                FROM taxi_requests tr
                WHERE tr.type_of_ride = 'own_vehicle'
            '''

            # Build WHERE conditions
            where_conditions = []
            params = []

            # Employee filter (search by name, email, or emp_code)
            if employee_filter:
                where_conditions.append('''
                    (tr.employee_name ILIKE %s OR
                     tr.employee_email ILIKE %s OR
                     tr.emp_code ILIKE %s)
                ''')
                search_term = f'%{employee_filter}%'
                params.extend([search_term, search_term, search_term])

            # Date range filter
            if date_range_filter:
                if date_range_filter == 'today':
                    where_conditions.append('DATE(tr.created_at) = CURRENT_DATE')
                elif date_range_filter == 'week':
                    where_conditions.append('tr.created_at >= NOW() - INTERVAL \'7 days\'')
                elif date_range_filter == 'month':
                    where_conditions.append('tr.created_at >= NOW() - INTERVAL \'30 days\'')

            # Combine query with filters
            if where_conditions:
                query = base_query + ' AND ' + ' AND '.join(where_conditions) + ' ORDER BY tr.created_at DESC'
            else:
                query = base_query + ' ORDER BY tr.created_at DESC'

            print(f"🔍 Admin Own Vehicle Query: {query}")
            print(f"📊 Parameters: {params}")

            # Execute the filtered query
            c.execute(query, params)
            requests = c.fetchall()

            # Get statistics (always get total stats, not filtered)
            c.execute('''
                SELECT
                    COUNT(*) as total_requests,
                    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as this_month,
                    COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as this_week
                FROM taxi_requests
                WHERE type_of_ride = 'own_vehicle'
            ''')
            stats = c.fetchone()

            total_requests = stats[0] if stats else 0
            this_month = stats[1] if stats else 0
            this_week = stats[2] if stats else 0

            print(f"✅ Found {len(requests)} own vehicle request records")

    except Exception as e:
        print(f"❌ Error fetching admin own vehicle data: {e}")
        traceback.print_exc()
        flash('Error loading own vehicle request data', 'error')
        requests = []
        total_requests = 0
        this_month = 0
        this_week = 0

    finally:
        db_pool.putconn(conn)

    return render_template('admin_own_vehicle.html',
                         requests=requests,
                         total_requests=total_requests,
                         this_month=this_month,
                         this_week=this_week,
                         admin=admin,
                         current_filters={
                             'employee': employee_filter,
                             'date_range': date_range_filter
                         })

# =============================================================================
# HEALTH CHECK ENDPOINT (for Render deployment)
# =============================================================================
@app.route('/health')
def health_check():
    """Health check endpoint for Render deployment"""
    try:
        # Test database connection
        conn = db_pool.getconn()
        c = conn.cursor()
        c.execute('SELECT 1')
        c.close()
        db_pool.putconn(conn)
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# =============================================================================
# APPLICATION STARTUP
# =============================================================================
def start_scheduler():
    """Start the background scheduler for reminders"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=check_and_send_overdue_reminders,
        trigger=IntervalTrigger(minutes=30),
        id='overdue_reminders',
        name='Check and send overdue feedback reminders every 30 minutes',
        replace_existing=True
    )
    scheduler.start()
    print("✅ Scheduler started - overdue reminders will run every 30 minutes")
    return scheduler

# Initialize database and scheduler on module load (for gunicorn)
print("🚀 Initializing Taxi Management System...")
if test_db_connection():
    init_db()
    start_scheduler()
else:
    print("⚠️ Database connection failed - will retry on first request")

if __name__ == '__main__':
    print("🚀 Starting Taxi Management System (Development Mode)...")

    # Test database connection first
    if not test_db_connection():
        print("❌ Cannot start application - database connection failed")
        exit(1)

    # Initialize database
    init_db()

    # Start scheduler
    start_scheduler()

    print("✅ Starting Flask application...")
    port = int(os.environ.get('PORT', 9060))
    app.run(debug=False, host='0.0.0.0', port=port)
