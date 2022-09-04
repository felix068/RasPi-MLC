#!/bin/bash
echo 
echo -e "\033[31m == Confirmation... == \033[0m"
confirm()
{
    read -r -p "${1} [Y/n] " answer
    case "$answer" in
        [yY][eE][sS]|[yY]) 
            true
            ;;
        *)
            false
            ;;
    esac
}
if confirm "Are you sure to install the program ?"; then
    echo "The software will install..."
    sudo echo "deb http://archive.raspbian.org/raspbian/ bookworm main" | sudo tee /etc/apt/sources.list.d/armbian.list
    sudo printf 'Package: *\nPin: release n=bookworm\nPin-Priority: 100\n' | sudo tee --append /etc/apt/preferences.d/limit-bookw
    sudo apt update
    sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 9165938D90FDDD2E
    sudo apt update
    sudo apt install bluez-tools bluez-alsa-utils -y
    sudo rm /etc/asound.conf
    sudo echo -e "defaults.pcm.card 1\ndefaults.ctl.card 1" > /etc/asound.conf
    macad=0
    sudo ls /var/lib/bluetooth/ | tee macad.e
    macad=`cat macad.e`
    sudo rm macad.e
    sudo echo -e "[General]\nDiscoverable=true" > /var/lib/bluetooth/$macad/settings
    sudo rm /etc/bluetooth/main.conf
    cd /etc/bluetooth/
    sudo wget https://raw.githubusercontent.com/felix068/RasPi-MLC/main/main.conf
    cd  ~/
    echo "Define bluetooth name :"
    read bluetoothname
    sudo echo -e "PRETTY_HOSTNAME=$bluetoothname" > /etc/machine-info
    sudo systemctl enable bluetooth
    sudo systemctl start bluetooth
    cd /etc/systemd/system/
    sudo wget https://raw.githubusercontent.com/felix068/RasPi-MLC/main/bt-agent.service
    cd  ~/
    sudo systemctl enable bt-agent
    sudo systemctl start bt-agent
    sudo rm /etc/default/bluez-alsa
    sudo echo -e 'OPTIONS="--profile=a2dp-sink"' > /etc/default/bluez-alsa
    cd /etc/systemd/system/
    sudo wget https://raw.githubusercontent.com/felix068/RasPi-MLC/main/aplay.service
    cd  ~/
    sudo systemctl enable aplay
    sudo systemctl start aplay
    
    sudo apt update
    sudo apt full-upgrade -y
    sudo apt-get install xserver-xorg-input-evdev xinput-calibrator xorg unclutter chromium-browser -y
    sudo cp -rf /usr/share/X11/xorg.conf.d/10-evdev.conf /usr/share/X11/xorg.conf.d/45-evdev.conf
    sudo rm /home/pi/.profile
    sudo rm /home/pi/.xinitrc
    cd /home/pi/
    sudo wget https://raw.githubusercontent.com/felix068/Working_Raspi_Kiosk/main/.profile
    sudo wget https://raw.githubusercontent.com/felix068/RasPi-MLC/main/.xinitrc
    cd /
    sudo wget https://raw.githubusercontent.com/felix068/Working_Raspi_Kiosk/main/st.sh
    echo -e "\033[31m The program setting your config file \033[0m"
    sudo rm /boot/config.txt
    cd /boot/
    sudo wget ""https://raw.githubusercontent.com/felix068/WP_Kiosk_Raspi/main/Preset/5inch%20HDMI%20LCD%20V2%20-800X480%20XPT2046/config.txt""
    echo -e "\033[31m The program setting Xorg (X11) \033[0m"
    cd /etc/X11/xorg.conf.d/
    sudo wget ""https://raw.githubusercontent.com/felix068/WP_Kiosk_Raspi/main/Preset/5inch%20HDMI%20LCD%20V2%20-800X480%20XPT2046/98-dietpi-disable_dpms.conf""
    echo -e "\033[31m The program setting your screen resolution and chromium argument \033[0m"
    cd  ~/
    echo -e "\033[31m The operation was done ! \033[0m"
else
    echo "The operation was canceled by the user."
fi

confirm()
{
    read -r -p "${1} [Y/n] " answer
    case "$answer" in
        [yY][eE][sS]|[yY]) 
            true
            ;;
        *)
            false
            ;;
    esac
}
if confirm "Do you want to restart ?"; then
    echo "Reboot."
    sudo reboot
else
    echo "The operation was canceled."
fi
