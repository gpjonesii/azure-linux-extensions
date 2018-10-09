import os
import os.path
import platform
import subprocess
import re
import sys

operation = None
outFile = '/tmp/omsresults.out'
openFile = open(outFile, 'w+')

def main():
    # Determine the operation being executed
    global operation
    try:
        option = sys.argv[1]
        if re.match('^([-/]*)(preinstall)', option):
            operation = 'preinstall'
        elif re.match('^([-/]*)(postinstall)', option):
            operation = 'postinstall'
        elif re.match('^([-/]*)(status)', option):
            operation = 'status'
    except:
        if operation is None:
            print "No operation specified. run with 'preinstall' or 'postinstall'"
    
    run_operation()

def is_vm_supported_for_extension():
    
    global vm_supported, vm_dist, vm_ver
    supported_dists = {'redhat' : ['6', '7'], # CentOS
                       'centos' : ['6', '7'], # CentOS
                       'red hat' : ['6', '7'], # Oracle, RHEL
                       'oracle' : ['6', '7'], # Oracle
                       'debian' : ['8', '9'], # Debian
                       'ubuntu' : ['14.04', '16.04', '18.04'], # Ubuntu
                       'suse' : ['12'] #SLES
    }

    try:
        vm_dist, vm_ver, vm_id = platform.linux_distribution()
    except AttributeError:
        vm_dist, vm_ver, vm_id = platform.dist()

    vm_supported = False

    # Find this VM distribution in the supported list
    for supported_dist in supported_dists.keys():
        if not vm_dist.lower().startswith(supported_dist):
            continue

        # Check if this VM distribution version is supported
        vm_ver_split = vm_ver.split('.')
        for supported_ver in supported_dists[supported_dist]:
            supported_ver_split = supported_ver.split('.')

            # If vm_ver is at least as precise (at least as many digits) as
            # supported_ver and matches all the supported_ver digits, then
            # this VM is guaranteed to be supported
            vm_ver_match = True
            for idx, supported_ver_num in enumerate(supported_ver_split):
                try:
                    supported_ver_num = int(supported_ver_num)
                    vm_ver_num = int(vm_ver_split[idx])
                except IndexError:
                    vm_ver_match = False
                    break
                if vm_ver_num is not supported_ver_num:
                    vm_ver_match = False
                    break
            if vm_ver_match:
                vm_supported = True
                break

        if vm_supported:
            break

    return vm_supported, vm_dist, vm_ver

def replace_items(infile,old_word,new_word):
    if not os.path.isfile(infile):
        print "Error on replace_word, not a regular file: "+infile
        sys.exit(1)

    f1=open(infile,'r').read()
    f2=open(infile,'w')
    m=f1.replace(old_word,new_word)
    f2.write(m)

def linux_detect_installer():
    global INSTALLER
    INSTALLER=None
    if vm_supported and (vm_dist.startswith('Ubuntu') or vm_dist.startswith('debian')):
        INSTALLER='APT'
    elif vm_supported and (vm_dist.startswith('CentOS') or vm_dist.startswith('Oracle') or vm_dist.startswith('Red Hat')):
        INSTALLER='YUM'
    elif vm_supported  and vm_dist.startswith('SUSE Linux'):
        INSTALLER='ZYPPER'

def install_additional_packages():
    #Add additional packages command here
    if INSTALLER == 'APT':
        os.system('apt-get -y install wget apache2 \
                && service apache2 start \
                && echo "mysql-server mysql-server/root_password password password" | debconf-set-selections \
                && echo "mysql-server mysql-server/root_password_again password password" | debconf-set-selections \
                && apt-get install -y mysql-server \
                && service mysql start')
    elif INSTALLER == 'YUM':
        os.system('yum install -y wget httpd \
                && service httpd start\
                && wget http://repo.mysql.com/mysql-community-release-el6-5.noarch.rpm \
                && yum localinstall -y mysql-community-release-el6-5.noarch.rpm \
                && yum install -y mysql-community-server \
                && service mysqld start')
    elif INSTALLER == 'ZYPPER':
        os.system('zypper install -y wget httpd \
                && service apache2 start \
                && zypper install mysql-server mysql-devel mysql \
                && service mysql start')

def disable_dsc():
    os.system('/opt/microsoft/omsconfig/Scripts/OMS_MetaConfigHelper.py --disable')
    # Pending_mof = '/etc/opt/omi/conf/omsconfig/configuration/Pending.mof'
    # Current_mof = '/etc/opt/omi/conf/omsconfig/configuration/Pending.mof'
    # if os.path.isfile(Pending_mof) or os.path.isfile(Current_mof):
    #     os.remove(Pending_mof)
    #     os.remove(Current_mof)

def enable_dsc():
    os.system('/opt/microsoft/omsconfig/Scripts/OMS_MetaConfigHelper.py --enable')

def apache_mysql_conf():
    apache_conf_dir = '/etc/opt/microsoft/omsagent/conf/omsagent.d/apache_logs.conf'
    mysql_conf_dir = '/etc/opt/microsoft/omsagent/conf/omsagent.d/mysql_logs.conf'
    apache_access_path_string = '/usr/local/apache2/logs/access_log /var/log/apache2/access.log /var/log/httpd/access_log /var/log/apache2/access_log'
    apache_error_path_string = '/usr/local/apache2/logs/error_log /var/log/apache2/error.log /var/log/httpd/error_log /var/log/apache2/error_log'
    mysql_general_path_string = '/var/log/mysql/mysql.log'
    mysql_error_path_string = '/var/log/mysql/error.log'
    mysql_slowquery_path_string = '/var/log/mysql/mysql-slow.log'

    if INSTALLER == 'APT':
        replace_items(apache_conf_dir, apache_access_path_string, '/var/log/apache2/access.log')
        replace_items(apache_conf_dir, apache_error_path_string, '/var/log/apache2/error.log')
        # replace_items(mysql_conf_dir, mysql_general_path_string, '/var/log/mysql/mysql.log')
        # replace_items(mysql_conf_dir, mysql_error_path_string, '/var/log/mysql/error.log')
        # replace_items(mysql_conf_dir, mysql_slowquery_path_string, '/var/log/mysql/mysql-slow.log')
    elif INSTALLER == 'YUM':
        replace_items(apache_conf_dir, apache_access_path_string, '/var/log/httpd/access_log')
        replace_items(apache_conf_dir, apache_error_path_string, '/var/log/httpd/error_log')
        # replace_items(mysql_conf_dir, mysql_general_path_string, '/var/log/mysqld.log')
        # replace_items(mysql_conf_dir, mysql_error_path_string, '/var/log/mysqld.log')
        # replace_items(mysql_conf_dir, mysql_slowquery_path_string, '/var/log/mysqld.log')
    elif INSTALLER == 'ZYPPER':
        replace_items(apache_conf_dir, apache_access_path_string, '/var/log/apache2/access_log')
        replace_items(apache_conf_dir, apache_error_path_string, '/var/log/apache2/error_log')
        # replace_items(mysql_conf_dir, mysql_general_path_string, '/var/log/mysql/mysqld.log')
        # replace_items(mysql_conf_dir, mysql_error_path_string, '/var/log/mysql/mysqld.log')
        # replace_items(mysql_conf_dir, mysql_slowquery_path_string, '/var/log/mysql/mysqld.log')

def copy_config_files():
    os.system('cp /etc/opt/microsoft/omsagent/sysconf/omsagent.d/apache_logs.conf /etc/opt/microsoft/omsagent/conf/omsagent.d/apache_logs.conf')
    #os.system('cp /etc/opt/microsoft/omsagent/sysconf/omsagent.d/mysql_logs.conf /etc/opt/microsoft/omsagent/conf/omsagent.d/mysql_logs.conf')
    apache_mysql_conf()

def restart_services():
    os.system('/opt/omi/bin/service_control restart \
                && /opt/microsoft/omsagent/bin/service_control restart')


'''
Common logic to run any command and check/get its output for further use
'''
def execCommand(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True)
        return out
    except subprocess.CalledProcessError as e:
        print(e.returncode)
        return (e.returncode)

'''
Common logic to save command outputs
'''
def writeLogOutput(out):
    if(type(out) != str): out=str(out)
    openFile.write(out + '\n')
    openFile.write('-' * 80)
    openFile.write('\n')
    return

'''
Common logic to save command itself
'''
def writeLogCommand(cmd):
    print(cmd)
    openFile.write(cmd + '\n')
    openFile.write('=' * 40)
    openFile.write('\n')
    return

def result_commands():
    cmd='waagent --version'
    out=execCommand(cmd)
    writeLogCommand(cmd)
    writeLogOutput(out)
    cmd='/opt/microsoft/omsagent/bin/omsadmin.sh -l'
    out=execCommand(cmd)
    writeLogCommand(cmd)
    writeLogOutput(out)
    cmd='scxadmin -status'
    out=execCommand(cmd)
    writeLogCommand(cmd)
    writeLogOutput(out)
    if INSTALLER == 'APT':
        dpkg_commands()
    elif INSTALLER == 'YUM' or INSTALLER == 'ZYPPER':
        rpm_commands()
    cmd='ps -ef | egrep "omsagent|omi"'
    out=execCommand(cmd)
    writeLogCommand(cmd)
    writeLogOutput(out)
    cmd='/opt/microsoft/omsagent/bin/service_control restart'
    out=execCommand(cmd)
    writeLogCommand(cmd)
    writeLogOutput(out)
    cmd='/opt/omi/bin/service_control restart'
    out=execCommand(cmd)
    writeLogCommand(cmd)
    writeLogOutput(out)

def dpkg_commands():
    cmd='dpkg -s omi'
    out=execCommand(cmd)
    writeLogCommand(cmd)
    writeLogOutput(out)
    cmd='dpkg -s omsagent'
    out=execCommand(cmd)
    writeLogCommand(cmd)
    writeLogOutput(out)
    cmd='dpkg -s omsconfig'
    out=execCommand(cmd)
    writeLogCommand(cmd)
    writeLogOutput(out)
    cmd='dpkg -s scx'
    out=execCommand(cmd)
    writeLogCommand(cmd)
    writeLogOutput(out)

def rpm_commands():
    cmd='rpm -qR omi'
    out=execCommand(cmd)
    writeLogCommand(cmd)
    writeLogOutput(out)
    cmd='rpm -qR omsagent'
    out=execCommand(cmd)
    writeLogCommand(cmd)
    writeLogOutput(out)
    cmd='rpm -qR omsconfig'
    out=execCommand(cmd)
    writeLogCommand(cmd)
    writeLogOutput(out)
    cmd='rpm -qR scx'
    out=execCommand(cmd)
    writeLogCommand(cmd)
    writeLogOutput(out)

def run_operation():
    vm_supported, vm_dist, vm_ver = is_vm_supported_for_extension()
    linux_detect_installer()
    if not vm_supported:
        print "Unsupported operating system: {0} {1}".format(vm_dist, vm_ver)
    else:
        if operation == 'preinstall':
            install_additional_packages()
        elif operation == 'postinstall':
            copy_config_files()
            enable_dsc()
            restart_services()
            writeLogOutput('PostInstall Status:')
            result_commands()
        elif operation == 'status':
            result_commands()


if __name__ == '__main__' :
    main()