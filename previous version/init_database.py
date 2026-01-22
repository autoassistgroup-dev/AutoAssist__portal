#!/usr/bin/env python3
"""
AutoAssistGroup Database Initialization Script

This script creates the complete database schema for a new MongoDB database,
including all collections, indexes, and initial data required for the
support ticket management system.

Usage:
    python init_database.py

Author: AutoAssistGroup Development Team
"""

import os
import sys
from datetime import datetime
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection string
MONGODB_URI = "mongodb+srv://therty243:m8I8QeexWXLlV7OD@cluster0.v97rdo1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

def connect_to_mongodb():
    """Connect to MongoDB and return client and database"""
    try:
        client = MongoClient(MONGODB_URI)
        # Test the connection
        client.admin.command('ping')
        logger.info("✅ Successfully connected to MongoDB")
        
        # Get or create the database
        db = client.support_tickets
        logger.info(f"✅ Using database: {db.name}")
        
        return client, db
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        sys.exit(1)

def create_collections(db):
    """Create all required collections"""
    collections = [
        'tickets',
        'replies', 
        'members',
        'ticket_assignments',
        'ticket_metadata',
        'technicians',
        'ticket_statuses',
        'roles',
        'common_documents',
        'common_document_metadata'  # 🚀 NEW: Collection for common document metadata
    ]
    
    logger.info("📚 Creating collections...")
    for collection_name in collections:
        if collection_name not in db.list_collection_names():
            db.create_collection(collection_name)
            logger.info(f"  ✅ Created collection: {collection_name}")
        else:
            logger.info(f"  ℹ️  Collection already exists: {collection_name}")

def create_indexes(db):
    """Create all required indexes for optimal performance"""
    logger.info("🔍 Creating indexes...")
    
    # Tickets collection indexes
    try:
        db.tickets.create_index("ticket_id", unique=True, background=False)
        db.tickets.create_index("thread_id", unique=True, background=False)
        db.tickets.create_index([("email", 1), ("status", 1)], background=False)
        db.tickets.create_index([("created_at", -1)], background=False)
        db.tickets.create_index([("status", 1), ("priority", 1)], background=False)
        db.tickets.create_index([("has_warranty", 1)], background=False)
        db.tickets.create_index([("has_attachments", 1)], background=False)
        db.tickets.create_index([("warranty_forms_count", 1)], background=False)
        db.tickets.create_index([("total_attachments", 1)], background=False)
        db.tickets.create_index([("processing_method", 1)], background=False)
        db.tickets.create_index([("has_warranty", 1), ("created_at", -1)], background=False)
        db.tickets.create_index([("has_attachments", 1), ("status", 1)], background=False)
        logger.info("  ✅ Created tickets indexes")
    except Exception as e:
        logger.warning(f"  ⚠️  Some tickets indexes already exist: {e}")
    
    # Replies collection indexes
    try:
        db.replies.create_index([("ticket_id", 1), ("created_at", 1)], background=False)
        logger.info("  ✅ Created replies indexes")
    except Exception as e:
        logger.warning(f"  ⚠️  Some replies indexes already exist: {e}")
    
    # Ticket assignments indexes
    try:
        db.ticket_assignments.create_index([("ticket_id", 1), ("member_id", 1)], background=False)
        logger.info("  ✅ Created ticket_assignments indexes")
    except Exception as e:
        logger.warning(f"  ⚠️  Some ticket_assignments indexes already exist: {e}")
    
    # Ticket metadata indexes
    try:
        db.ticket_metadata.create_index([("ticket_id", 1), ("key", 1)], background=False)
        logger.info("  ✅ Created ticket_metadata indexes")
    except Exception as e:
        logger.warning(f"  ⚠️  Some ticket_metadata indexes already exist: {e}")
    
    # Members collection indexes
    try:
        db.members.create_index("user_id", unique=True, background=False)
        logger.info("  ✅ Created members indexes")
    except Exception as e:
        logger.warning(f"  ⚠️  Some members indexes already exist: {e}")
    
    # Common documents indexes
    try:
        db.common_documents.create_index([("name", 1)], background=False)
        db.common_documents.create_index([("type", 1)], background=False)
        db.common_documents.create_index([("created_at", -1)], background=False)
        logger.info("  ✅ Created common_documents indexes")
    except Exception as e:
        logger.warning(f"  ⚠️  Some common_documents indexes already exist: {e}")
    
    # Common document metadata indexes
    try:
        db.common_document_metadata.create_index([("document_id", 1), ("key", 1)], background=False)
        db.common_document_metadata.create_index([("document_id", 1)], background=False)
        logger.info("  ✅ Created common_document_metadata indexes")
    except Exception as e:
        logger.warning(f"  ⚠️  Some common_document_metadata indexes already exist: {e}")

def create_initial_users(db):
    """Create initial admin and technical director users"""
    logger.info("👥 Creating initial users...")
    
    # Admin user
    admin_exists = db.members.find_one({"user_id": "admin001"})
    if not admin_exists:
        admin_user = {
            "name": "Admin",
            "role": "Administrator",
            "gender": "male",
            "user_id": "admin001",
            "password_hash": generate_password_hash("admin@123"),
            "created_at": datetime.now(),
            "is_active": True
        }
        db.members.insert_one(admin_user)
        logger.info("  ✅ Created admin user (admin001 / admin@123)")
    else:
        logger.info("  ℹ️  Admin user already exists")
    
    # Technical Director user
    tech_director_exists = db.members.find_one({"user_id": "marc001"})
    if not tech_director_exists:
        tech_director_user = {
            "name": "Marc (Technical Director)",
            "role": "Technical Director",
            "gender": "male",
            "user_id": "marc001",
            "password_hash": generate_password_hash("tech@123"),
            "created_at": datetime.now(),
            "email": "marc@autoassistgroup.com",
            "department": "Technical",
            "is_active": True
        }
        db.members.insert_one(tech_director_user)
        logger.info("  ✅ Created technical director user (marc001 / tech@123)")
    else:
        logger.info("  ℹ️  Technical director user already exists")

def create_initial_technicians(db):
    """Create initial technician records"""
    logger.info("🔧 Creating initial technicians...")
    
    if db.technicians.count_documents({}) == 0:
        initial_technicians = [
            {"name": "Ryan", "role": "Senior Technician", "email": "ryan@autoassistgroup.com"},
            {"name": "Declan", "role": "Technician", "email": "declan@autoassistgroup.com"},
            {"name": "Ross H", "role": "Lead Technician", "email": "ross.h@autoassistgroup.com"},
            {"name": "Ross K", "role": "Technician", "email": "ross.k@autoassistgroup.com"},
            {"name": "Ray", "role": "Senior Technician", "email": "ray@autoassistgroup.com"},
            {"name": "Craig", "role": "Technician", "email": "craig@autoassistgroup.com"},
            {"name": "Karl", "role": "Lead Technician", "email": "karl@autoassistgroup.com"},
            {"name": "Matthew", "role": "Technician", "email": "matthew@autoassistgroup.com"},
            {"name": "Lewis", "role": "Senior Technician", "email": "lewis@autoassistgroup.com"},
            {"name": "Luke", "role": "Technician", "email": "luke@autoassistgroup.com"}
        ]
        
        for tech_data in initial_technicians:
            technician_data = {
                "name": tech_data["name"],
                "role": tech_data["role"],
                "email": tech_data["email"],
                "is_active": True,
                "created_at": datetime.now()
            }
            db.technicians.insert_one(technician_data)
        
        logger.info(f"  ✅ Created {len(initial_technicians)} initial technicians")
    else:
        logger.info("  ℹ️  Technicians already exist")

def create_default_ticket_statuses(db):
    """Create default ticket statuses"""
    logger.info("📋 Creating default ticket statuses...")
    
    if db.ticket_statuses.count_documents({}) == 0:
        default_statuses = [
            {'name': 'New', 'color': '#f59e0b', 'description': 'Newly created ticket', 'order': 1},
            {'name': 'Form Sent', 'color': '#3b82f6', 'description': 'Initial form sent to customer', 'order': 2},
            {'name': 'Awaiting Submission', 'color': '#8b5cf6', 'description': 'Waiting for customer submission', 'order': 3},
            {'name': 'Under Review', 'color': '#f59e0b', 'description': 'Ticket under review', 'order': 4},
            {'name': 'Info Requested', 'color': '#06b6d4', 'description': 'Additional information requested', 'order': 5},
            {'name': 'Warranty Form Received', 'color': '#10b981', 'description': 'Warranty form has been received', 'order': 6},
            {'name': 'Referred to Tech Director', 'color': '#8b5cf6', 'description': 'Escalated to technical director', 'order': 7},
            {'name': 'Approved - Revisit Booked', 'color': '#10b981', 'description': 'Claim approved, revisit scheduled', 'order': 8},
            {'name': 'Declined - Not Covered', 'color': '#ef4444', 'description': 'Claim declined, not under warranty', 'order': 9},
            {'name': 'Closed', 'color': '#6b7280', 'description': 'Ticket resolved and closed', 'order': 10},
            {'name': 'Revisit', 'color': '#f59e0b', 'description': 'Ticket needs to be revisited', 'order': 11}
        ]
        
        for status in default_statuses:
            status['created_at'] = datetime.now()
            status['is_active'] = True
            db.ticket_statuses.insert_one(status)
        
        logger.info(f"  ✅ Created {len(default_statuses)} default ticket statuses")
    else:
        logger.info("  ℹ️  Ticket statuses already exist")

def create_default_roles(db):
    """Create default user roles"""
    logger.info("🎭 Creating default roles...")
    
    default_roles = [
        {
            "name": "Administrator",
            "description": "Full system access with user management and configuration controls",
            "permissions": ["full_access", "user_management", "system_config", "ticket_management"],
            "level": 1,
            "color": "#6366f1"
        },
        {
            "name": "Technical Director",
            "description": "Technical oversight with referred ticket review and assessment",
            "permissions": ["referred_tickets", "technical_assessment", "reports", "ticket_management"],
            "level": 2,
            "color": "#f59e0b"
        },
        {
            "name": "User",
            "description": "IT support team members with ticket management and technical assistance",
            "permissions": ["ticket_management", "it_support", "portal_assistance", "technical_help"],
            "level": 3,
            "color": "#10b981"
        }
    ]
    
    created_count = 0
    for role_data in default_roles:
        existing_role = db.roles.find_one({"name": role_data["name"]})
        if not existing_role:
            role_data['created_at'] = datetime.now()
            role_data['is_default'] = True
            db.roles.insert_one(role_data)
            created_count += 1
            logger.info(f"  ✅ Created role: {role_data['name']}")
    
    if created_count > 0:
        logger.info(f"  ✅ Created {created_count} default roles")
    else:
        logger.info("  ℹ️  All default roles already exist")

def verify_database_setup(db):
    """Verify that all collections and data were created successfully"""
    logger.info("🔍 Verifying database setup...")
    
    # Check collections
    collections = db.list_collection_names()
    expected_collections = [
        'tickets', 'replies', 'members', 'ticket_assignments',
        'ticket_metadata', 'technicians', 'ticket_statuses', 'roles', 'common_documents',
        'common_document_metadata'  # 🚀 NEW: Collection for common document metadata
    ]
    
    missing_collections = [col for col in expected_collections if col not in collections]
    if missing_collections:
        logger.error(f"  ❌ Missing collections: {missing_collections}")
    else:
        logger.info("  ✅ All collections present")
    
    # Check data counts
    admin_count = db.members.count_documents({"user_id": "admin001"})
    tech_director_count = db.members.count_documents({"user_id": "marc001"})
    technician_count = db.technicians.count_documents({})
    status_count = db.ticket_statuses.count_documents({})
    role_count = db.roles.count_documents({})
    
    logger.info(f"  📊 Data counts:")
    logger.info(f"    - Admin users: {admin_count}")
    logger.info(f"    - Tech Directors: {tech_director_count}")
    logger.info(f"    - Technicians: {technician_count}")
    logger.info(f"    - Ticket Statuses: {status_count}")
    logger.info(f"    - User Roles: {role_count}")
    
    return len(missing_collections) == 0

def main():
    """Main function to initialize the database"""
    logger.info("🚀 Starting AutoAssistGroup Database Initialization...")
    logger.info(f"🔗 Connecting to: {MONGODB_URI.split('@')[1] if '@' in MONGODB_URI else 'MongoDB'}")
    
    try:
        # Connect to MongoDB
        client, db = connect_to_mongodb()
        
        # Create database structure
        create_collections(db)
        create_indexes(db)
        
        # Create initial data
        create_initial_users(db)
        create_initial_technicians(db)
        create_default_ticket_statuses(db)
        create_default_roles(db)
        
        # Verify setup
        success = verify_database_setup(db)
        
        if success:
            logger.info("🎉 Database initialization completed successfully!")
            logger.info("🔑 Default login credentials:")
            logger.info("  - Admin: admin001 / admin@123")
            logger.info("  - Tech Director: marc001 / tech@123")
            logger.info("")
            logger.info("📝 Next steps:")
            logger.info("  1. Update your Vercel environment variables with the new MONGODB_URI")
            logger.info("  2. Redeploy your application")
            logger.info("  3. Test the login with the default credentials")
        else:
            logger.error("❌ Database initialization completed with errors")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        sys.exit(1)
    finally:
        if 'client' in locals():
            client.close()
            logger.info("🔌 MongoDB connection closed")

if __name__ == "__main__":
    main()
