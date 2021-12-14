import sys
import os
import paramiko  # pip install paramiko
import getpass  # pip install getpass
import time
import argparse
from colorama import Fore, Back, Style, init  # pip install colorama
from scp import SCPClient  # pip install scp
# pip install zipfile36
if sys.version_info >= (3, 6):
    import zipfile
else:
    import zipfile36 as zipfile

# settings
settings = {
    "host": "",  # aws server ip
    "user": "centos",  # aws ec2 username -- usually centos in a centos ec2
    "private_key_file": "/path/to/key.pem", # your private key file to login
    "deploy_path": "/usr/share/nginx/deploy",  # temprorary deployment path -- should be owned/accessible by centos user -- create this folder before using this script
    "app_path": "/usr/share/nginx/laravel",  # remote app path -- should be owned/accessible by nginx user -- where laravel works
    "filename": "deploy_" + str(time.time()) + ".zip",  # zip filename
    "directories": ['app', 'bootstrap', 'config', 'database', 'public', 'resources', 'routes', 'vendor'],  # folders to include in deploy
    "files": ['composer.json', 'composer.lock', 'artisan', 'server.php'] # files to include in deploy
}

# commands to call after deployment
commands = [
    "sudo mv " + settings['deploy_path'] + "/" + settings['filename'] + " " + settings['app_path'] + "/" + settings['filename'], # Move file from deploy/ to html/
    "sudo unzip -o " + settings['filename'],  # unzip files
    "sudo find . -type d -exec chmod 755 {} \;",  # remake chmod for uploaded folders
    "sudo find . -type f -exec chmod 644 {} \;",  # remake chmod for uploaded files
    "sudo chown -R nginx:nginx .",  # remake owner
    "sudo rm -rf " + settings['filename'],  # remove uploaded zipfile.
    "sudo -u nginx php artisan clear",
    "sudo -u nginx php artisan config:clear",
    "sudo -u nginx php artisan cache:clear",
    "sudo -u nginx php artisan view:clear",
    "sudo -u nginx php artisan migrate --force",
    "sudo php artisan queue:restart",
]


def progress(filename, size, sent):
    sys.stdout.write('-- Uploading %s progress: %.2f%% \r' % (settings['filename'], float(sent) / float(size) * 100))


def create_zip(arr, filesArr, filename):
    if os.path.exists(filename):
        print("File already exists, please re-run the command.")
        sys.exit()

    print("Started zipping.")
    zf = zipfile.ZipFile(filename, "w")


    try:
        #Files
        for one_file in filesArr:
            zf.write(one_file)

        # Directories
        for one_path in arr:
            zf.write(one_path)
            for dirname, sub_dirs, files in os.walk(one_path):
                for file in files:
                    zf.write(os.path.join(dirname, file))
        zf.close()
        print("Finished zipping.")

    except KeyboardInterrupt:
        zf.close()
        print("User exit.")
        clean()
        sys.exit()


def upload(host, user, deploy_path, app_path, filename):
    print("Connecting to host..")
    # password = getpass.getpass(prompt='Please enter user password: ', stream=None)

    full_path = deploy_path + "/" + filename

    try:
        k = paramiko.RSAKey.from_private_key_file(settings['private_key_file'])
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, 22, user, pkey = k)

        print("Connected to host: " + host)

        # Upload zipped file
        with SCPClient(ssh.get_transport(), progress=progress) as scp:
            print("Starting upload")
            scp.put(filename, full_path)

        scp.close()
        # Done uploading.
        print("-- Finished uploading " + filename)

        # Send post-upload commands.
        print("Sending commands")
        for com in commands:
            print("-- Command " + com)
            stdin, stdout, stderr = ssh.exec_command("cd " + app_path + ";" + com)
            output = 0
            for line in iter(stdout.readline, ""):
                print(line, end="")
                output += 1
                sys.stdout.write("-- %s working. \r" % str(output))
            print("---- " + str(output) + " total outputs.")
            print("---- Done")

        print("Sent commands")
        print("Finished deploying")
        clean()
        sys.exit()
    except paramiko.ssh_exception.AuthenticationException:
        print("Authentication Error.")
        # clean()
        sys.exit()
    except KeyboardInterrupt:
        print("User exit.")
        # clean()
        sys.exit()
    except SystemExit:
        print("System exit.")
        # clean()
        sys.exit()


def clean():
    if os.path.exists(settings['filename']):
        os.remove(settings['filename'])


def start():
    print("")
    print("*" * 50)
    print("#")
    print("# Host: " + Fore.GREEN + settings['host'] + Style.RESET_ALL)
    print("# Deployment Path: " + Fore.GREEN + settings['deploy_path'] + Style.RESET_ALL)
    print("# App Path: " + Fore.GREEN + settings['app_path'] + Style.RESET_ALL)
    print("# Directories: " + Fore.GREEN + "/, ".join(settings['directories']) + "/" + Style.RESET_ALL)
    print("# Files: " + Fore.GREEN + ", ".join(settings['files']) + Style.RESET_ALL)
    print("# Zip File: " + Fore.GREEN + settings['filename'] + Style.RESET_ALL)
    print("#")
    print("*" * 50)


def run():
    init()
    start()
    create_zip(settings['directories'], settings['files'], settings['filename'])

    if len(sys.argv) > 1:
        if sys.argv[1] == '--zip':
            print("Zip Only. Exit;")
            sys.exit()

    upload(settings['host'], settings['user'], settings['deploy_path'], settings['app_path'], settings['filename'])


run()
