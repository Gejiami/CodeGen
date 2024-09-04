"# CodeGen" 
Installation and Setup Guide
1. Environment Setup
It is recommended to perform the installation and setup on an Ubuntu Linux system. 
Ensure that Git, Python3, and pip are installed on your system.

(1)Install Git, Python3, and pip
```
sudo apt-get update
sudo apt-get install git
sudo apt-get install python3
sudo apt-get install python3-pip
```

(2)Install Project Dependencies
Navigate to the project's root directory and install the required Python packages.
```
cd jxg240
pip install -r requirements.txt
```

(3)Flutter Project Setup
The project supports both Flutter and Python. To use Flutter, you need to follow the official Flutter tutorial to install Flutter and Dart SDK.
Refer to the official installation guide: https://docs.flutter.dev/get-started/install/linux/web

(4)Configure Flutter Version Manager
Install and activate Flutter Version Manager (FVM) using command.
Ensure that fvm is added to your PATH environment variable.
```
dart pub global activate fvm
export PATH="$PATH":"$HOME/.pub-cache/bin"
```

(5)Configure Environment Variables
Modify and configure environment variables according to the .env file in the root directory of the project. This includes setting your OpenAI API key and GitHub token. 


2 Run Example Flutter Application
Since we can not publish the source code of the application provided by our partner company, we developed an easy flutter application for test use according the official tutorial and have uploaded it to github.
This is a simple Flutter app designed to randomly generate and save nicknames, primarily for testing purposes. The actual project may involve more files and configurations.

(1)Clone GitHub Project Code
Before putting forward any change requests , you can first clone the project from GitHub to check its contents. To ensure consistency with the paths used later, navigate to your home directory first.
```
cd ~
git clone https://github.com/Gejiami/flutter_test.git
```

(2)Navigate to the root directory of the Flutter project and run the app
If your Linux system supports GUI: 
```
flutter run
```

If GUI is not supported, run it in web server mode: 
```
flutter run -d web-server
```
Obtain the port information where Flutter is running and forward it to your local server using the following command
```
ssh -L <flutter_port>:localhost:<flutter_port> <remote_user>@<remote_ip>
```

3. Run Python Script
Open a new terimal to navigate to the jxg240/task project directory.
```
cd jxg240/task
```

Run the Python script to perform the specified task
```
python ./run_task.py --repo 'Gejiami/flutter_test' --repo_type 'github' --language 'flutter' --model_name 'gpt-4o' --user_instruction '''Increase the size of the text box on the home page.'''
```
or directly run bash command
```
sh bash_run.sh
```

After the script completes, return to the terminal where you started the flutter_test project and press R to perform a hot restart.
Go back to your local server, refresh the webpage, and you should see the updated changes.
