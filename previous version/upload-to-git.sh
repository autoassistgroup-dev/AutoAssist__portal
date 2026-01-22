#!/bin/bash

# AutoAssistGroup - Upload to Git Repository Script
# This script helps you upload your application to a Git repository

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[INFO] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Check if git is installed
check_git() {
    if ! command -v git &> /dev/null; then
        error "Git is not installed. Please install Git first."
    fi
}

# Initialize git repository
init_git() {
    log "Initializing Git repository..."
    
    if [[ ! -d ".git" ]]; then
        git init
        log "Git repository initialized"
    else
        log "Git repository already exists"
    fi
}

# Add files to git
add_files() {
    log "Adding files to Git..."
    
    # Add all files
    git add .
    
    # Show what will be committed
    echo
    info "Files to be committed:"
    git status --short
    echo
}

# Commit files
commit_files() {
    log "Committing files..."
    
    # Get commit message from user
    read -p "Enter commit message (or press Enter for default): " commit_message
    
    if [[ -z "$commit_message" ]]; then
        commit_message="Initial commit - AutoAssistGroup EC2 deployment"
    fi
    
    git commit -m "$commit_message"
    log "Files committed successfully"
}

# Add remote repository
add_remote() {
    log "Setting up remote repository..."
    
    # Get repository URL from user
    echo
    info "Please provide your Git repository URL:"
    echo "Examples:"
    echo "  - GitHub: https://github.com/username/repository-name.git"
    echo "  - GitLab: https://gitlab.com/username/repository-name.git"
    echo "  - Bitbucket: https://bitbucket.org/username/repository-name.git"
    echo
    
    read -p "Enter repository URL: " repo_url
    
    if [[ -z "$repo_url" ]]; then
        error "Repository URL is required"
    fi
    
    # Add remote origin
    git remote add origin "$repo_url" 2>/dev/null || {
        warning "Remote 'origin' already exists. Updating URL..."
        git remote set-url origin "$repo_url"
    }
    
    log "Remote repository added: $repo_url"
}

# Push to repository
push_to_repo() {
    log "Pushing to repository..."
    
    # Get branch name
    read -p "Enter branch name (or press Enter for 'main'): " branch_name
    
    if [[ -z "$branch_name" ]]; then
        branch_name="main"
    fi
    
    # Push to repository
    git push -u origin "$branch_name"
    
    log "Successfully pushed to repository!"
}

# Create .gitignore file
create_gitignore() {
    log "Creating .gitignore file..."
    
    cat > .gitignore << EOF
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# Environment variables
.env
.env.local
.env.production

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Database
*.db
*.sqlite3

# Uploads
uploads/

# Backups
backups/

# Temporary files
*.tmp
*.temp

# Vercel
.vercel

# AWS
.aws/
EOF

    log ".gitignore file created"
}

# Main function
main() {
    echo "🚀 AutoAssistGroup - Git Upload Helper"
    echo "======================================"
    echo
    
    check_git
    create_gitignore
    init_git
    add_files
    commit_files
    add_remote
    push_to_repo
    
    echo
    log "✅ Successfully uploaded to Git repository!"
    echo
    info "Next steps:"
    echo "1. Connect to your EC2 instance"
    echo "2. Clone the repository: git clone YOUR_REPO_URL"
    echo "3. Run the deployment script: sudo ./deploy-amazon-linux.sh"
    echo
    info "Repository URL: $(git remote get-url origin)"
}

# Run main function
main "$@"
