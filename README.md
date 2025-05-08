# Chrome Extension Auditor

The Chrome Extension Auditor is a command-line tool designed to help security researchers and developers audit Chrome Extensions. 
It automates the download of extensions and runs static analysis to identify external APIs, hardcoded secrets, and potentially malicious patterns.

This manual will cover the prerequisites needed, as well as installation and configuration of the tool to help you get started quickly.

# Prerequisties

Please ensure you have the following installed on your system:  
• Python 3.10+  
• Git  
• Node.js and npm  
• pip  
Please note, the tool was developed on Ubuntu Linux, please use a Linux system for best results.

# Installation

Please follow these steps to install the Chrome Extension Auditor.  
1. Clone the Repository  
The repository can be found using the URL provided below:  
https://github.com/ParkinsonThomas/ExtensionAuditor

2. Python Dependencies  
Install Python dependencies using:  
pip install -r requirements.txt

3. JavaScript Dependencies  
Install JavaScript dependencies using:  
npm install –save-dev @babel/core @babel/cli @babel/preset-env @babel/parser @babel/traverse

4. Install Gitleaks  
Install Gitleaks from the repository URL provided below:  
https://github.com/gitleaks/gitleaks

# Configuration

Configuration is driven by the "config.json" file.  

The options available to the user, from top to bottom they are as followed:  
• The database file.  
• The .txt file from which GUIDs will be scraped to (GUID_ListCreator) or read from (Extension_Scraper).  
• The directories to which extensions will be downloaded and extracted to.  
• Entropy filtering, if it is enabled and if so the filter value.  

Underneath these options are the modules listed, by default these are all set to "false", change to "true" to enable them.  

To add more modules simply copy the format for other modules with your module name.

# Usage

Before running, a DeepSeek API needs to be exported into the terminal (for API_Auditor.py), this can be done by running the following:  
export DEEPSEEK_API_KEY="YOUR-API-KEY"  

To run the tool, simply enter the following command based on your Python installation:  
python main.py  
python3 main.py  

To wipe the database, enter the following command based on your Python installation:  
python DB_Wipe.py  
python3 DB_Wipe.py  

Please note: to view results, the module "Display" must be enabled.  

To run Unit Tests, enter the following command based on your Python installation:  
python Run_Unit_Tests.py  
python3 Run_Unit_Tests.py  