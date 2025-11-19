#!/bin/bash

# Requirements Agent Setup Checker
# Verifies that all components are properly installed and configured

set -e

COLOR_GREEN='\033[0;32m'
COLOR_RED='\033[0;31m'
COLOR_YELLOW='\033[1;33m'
COLOR_BLUE='\033[0;34m'
COLOR_NC='\033[0m' # No Color

echo -e "${COLOR_BLUE}================================${COLOR_NC}"
echo -e "${COLOR_BLUE}Requirements Agent Setup Checker${COLOR_NC}"
echo -e "${COLOR_BLUE}================================${COLOR_NC}\n"

ERRORS=0
WARNINGS=0

# Function to check if file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${COLOR_GREEN}✓${COLOR_NC} Found: $1"
        return 0
    else
        echo -e "${COLOR_RED}✗${COLOR_NC} Missing: $1"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

# Function to check if directory exists
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${COLOR_GREEN}✓${COLOR_NC} Found directory: $1"
        return 0
    else
        echo -e "${COLOR_YELLOW}⚠${COLOR_NC} Missing directory: $1 (will be created automatically)"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi
}

# Function to check Python package
check_python_package() {
    if python3 -c "import $1" 2>/dev/null; then
        echo -e "${COLOR_GREEN}✓${COLOR_NC} Python package installed: $1"
        return 0
    else
        echo -e "${COLOR_RED}✗${COLOR_NC} Missing Python package: $1"
        echo -e "   Install with: pip install $2"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

echo -e "${COLOR_BLUE}[1/5] Checking Core Files${COLOR_NC}\n"

check_file "requirements_toolkit.py"
check_file "requirements_agent_filter.py"

echo ""

echo -e "${COLOR_BLUE}[2/5] Checking Documentation${COLOR_NC}\n"

check_file "REQUIREMENTS_AGENT_README.md"
check_file "REQUIREMENTS_AGENT_SETUP.md"
check_file "REQUIREMENTS_QUICKSTART.md"
check_file "REQUIREMENTS_EXAMPLES.md"

echo ""

echo -e "${COLOR_BLUE}[3/5] Checking Requirements Storage Structure${COLOR_NC}\n"

REQ_BASE_PATH="backend/data/requirements"

check_dir "$REQ_BASE_PATH"
check_dir "$REQ_BASE_PATH/backlog"
check_dir "$REQ_BASE_PATH/decided"
check_dir "$REQ_BASE_PATH/implemented"
check_dir "$REQ_BASE_PATH/deprecated"

if [ -f "$REQ_BASE_PATH/index.json" ]; then
    echo -e "${COLOR_GREEN}✓${COLOR_NC} Found: $REQ_BASE_PATH/index.json"
else
    echo -e "${COLOR_YELLOW}⚠${COLOR_NC} Missing: $REQ_BASE_PATH/index.json (will be created on first use)"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""

echo -e "${COLOR_BLUE}[4/5] Checking Python Dependencies${COLOR_NC}\n"

# Check for Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${COLOR_GREEN}✓${COLOR_NC} Python found: $PYTHON_VERSION"
else
    echo -e "${COLOR_RED}✗${COLOR_NC} Python 3 not found"
    ERRORS=$((ERRORS + 1))
fi

# Check for required packages
check_python_package "yaml" "pyyaml"
check_python_package "slugify" "python-slugify"

echo ""

echo -e "${COLOR_BLUE}[5/5] Checking Open WebUI Installation${COLOR_NC}\n"

# Check if Open WebUI backend exists
if [ -d "backend" ]; then
    echo -e "${COLOR_GREEN}✓${COLOR_NC} Open WebUI backend directory found"
else
    echo -e "${COLOR_YELLOW}⚠${COLOR_NC} backend/ directory not found"
    echo -e "   Are you running this from the Open WebUI root directory?"
    WARNINGS=$((WARNINGS + 1))
fi

# Check for webui.db
if [ -f "backend/data/webui.db" ]; then
    echo -e "${COLOR_GREEN}✓${COLOR_NC} Open WebUI database found"
else
    echo -e "${COLOR_YELLOW}⚠${COLOR_NC} backend/data/webui.db not found"
    echo -e "   Open WebUI may not be initialized yet"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""
echo -e "${COLOR_BLUE}================================${COLOR_NC}"
echo -e "${COLOR_BLUE}Setup Check Complete${COLOR_NC}"
echo -e "${COLOR_BLUE}================================${COLOR_NC}\n"

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${COLOR_GREEN}✓ All checks passed!${COLOR_NC}\n"
    echo -e "Your Requirements Agent setup looks good.\n"
    echo -e "Next steps:"
    echo -e "1. Open Open WebUI in your browser"
    echo -e "2. Go to Workspace → Tools"
    echo -e "3. Create a new tool and paste contents of requirements_toolkit.py"
    echo -e "4. Go to Admin Panel → Functions"
    echo -e "5. Create a new Filter and paste contents of requirements_agent_filter.py"
    echo -e "6. Start a chat and enable the Requirements Management Toolkit"
    echo -e "\nSee REQUIREMENTS_QUICKSTART.md for detailed instructions."
elif [ $ERRORS -eq 0 ]; then
    echo -e "${COLOR_YELLOW}⚠ Setup incomplete with $WARNINGS warning(s)${COLOR_NC}\n"
    echo -e "Some optional components are missing but the system should work."
    echo -e "Review warnings above for details."
else
    echo -e "${COLOR_RED}✗ Setup incomplete with $ERRORS error(s) and $WARNINGS warning(s)${COLOR_NC}\n"
    echo -e "Please fix the errors above before proceeding."
    echo -e "See REQUIREMENTS_AGENT_SETUP.md for help."
    exit 1
fi

echo ""

# Offer to create requirements structure
if [ ! -d "$REQ_BASE_PATH" ]; then
    echo -e "${COLOR_BLUE}Would you like to create the requirements folder structure now? (y/n)${COLOR_NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "\nCreating requirements folder structure..."
        mkdir -p "$REQ_BASE_PATH"/{backlog,decided,implemented,deprecated}

        # Create README
        cat > "$REQ_BASE_PATH/README.md" << 'EOF'
# Requirements Database

This folder contains requirements managed by the Open WebUI Requirements Agent.

## Structure

- `backlog/` - Proposed requirements awaiting review
- `decided/` - Accepted requirements ready for implementation
- `implemented/` - Implemented requirements
- `deprecated/` - Deprecated or rejected requirements
- `index.json` - Quick lookup index of all requirements

## Usage

Requirements are managed through the Open WebUI Requirements Agent using natural language conversation.
You can also manually edit requirements files - they will be picked up on the next index rebuild.

## Format

Each requirement is a markdown file with YAML frontmatter. See REQUIREMENTS_EXAMPLES.md for templates.
EOF

        # Create initial index
        cat > "$REQ_BASE_PATH/index.json" << EOF
{
  "last_updated": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "requirements": []
}
EOF

        echo -e "${COLOR_GREEN}✓${COLOR_NC} Requirements folder structure created successfully!"
        echo -e "\nLocation: $REQ_BASE_PATH"
        echo -e "You're all set! See REQUIREMENTS_QUICKSTART.md to begin."
    else
        echo -e "Skipped. The structure will be created automatically when you first use the toolkit."
    fi
fi

echo ""
