#!/bin/bash
commands='22'

RED='\033[1;91m'
CYAN='\033[1;96m'
PURPLE_LIGHT='\033[5;35m'
RESET='\033[0m'

start_process_line="${PURPLE_LIGHT}################################################################################"
end_process_line="################################################################################${RESET}"

logo="${CYAN}FunPayNEXT${RESET}"

clear
echo -e "$logo"


echo -e "\n\n${RED} * GitHub ${CYAN}github.com/xelawave/FunPayNEXT${RESET}"
echo -e "\n\n\n"


echo -ne "${CYAN}Введите имя пользователя, от имени которого будет запускаться бот (например, 'funpaynext'): ${RESET}"
while true; do
  read username

  if [[ "$username" =~ ^[a-zA-Z][a-zA-Z0-9_-]+$ ]]; then
    if id "$username" &>/dev/null; then
      echo -ne "\n${RED}Пользователь уже существует.${RESET} Использовать его? (y/n): "
      read use_existing

      if [[ "$use_existing" =~ ^[Yy]$ ]]; then
        echo -e "${CYAN}Будет использован существующий пользователь: $username${RESET}"
        break
      else
        echo -ne "${CYAN}Введите другое имя пользователя: ${RESET}"
      fi
    else
      break
    fi
  else
    echo -ne "\n${RED}Имя пользователя содержит недопустимые символы. ${CYAN}Имя должно начинаться с буквы и может включать только буквы, цифры, '_', или '-'. Пожалуйста, введите другое имя пользователя: ${RESET}"
  fi
done


distro_version=$(lsb_release -rs)


clear
echo -e "${start_process_line}\nДобавляю репозитории...\n${end_process_line}"


# 1
if ! sudo apt update ; then
  echo -e "${start_process_line}\nПроизошла ошибка при обновлении списка пакетов. (1/${commands})\n${end_process_line}"
  exit 2
fi

#2
if ! sudo apt install -y software-properties-common ; then
  echo -e "${start_process_line}\nПроизошла ошибка при установке software-properties-common. (2/${commands})\n${end_process_line}"
  exit 2
fi

#3
case $distro_version in
  "22.04" | "22.10" | "23.04" | "23.10" | "24.04" | "24.10") # Ubuntu 22.04 (Jammy Jellyfish), 22.10 (Kinetic Kudu), 23.04 (Lunar Lobster), 23.10 (Mantic Minotaur), 24.04 (Noble Numbat), 24.10 (Oracular Oriole)
    ;;
  "12") # Debian 12 (Bookworm)
    ;;
  "11") # Debian 11 (Bullseye)
    # TODO: Ошибка проверки ключа репозитория на некоторых машинах, хз почему, проще использовать костыль ввиде убунтовских deadsnakes
    # #3.1
    # if ! sudo curl -O https://people.debian.org/~paravoid/python-all/unofficial-python-all.asc ; then
    #   echo -e "${start_process_line}\nПроизошла ошибка при загрузке ключа репозитория. (3.1/${commands})\n${end_process_line}"
    #   exit 2
    # fi

    # #3.2
    # if ! sudo mv unofficial-python-all.asc /etc/apt/trusted.gpg.d/ ; then
    #   echo -e "${start_process_line}\nПроизошла ошибка при перемещении ключа репозитория. (3.2/${commands})\n${end_process_line}"
    #   exit 2
    # fi

    # #3.3
    # if ! echo "deb http://people.debian.org/~paravoid/python-all $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/python-all.list ; then
    #   echo -e "${start_process_line}\nПроизошла ошибка при добавлении репозитория. (3.3/${commands})\n${end_process_line}"
    #   exit 2
    # fi

    #3.1
    if ! sudo apt install -y gnupg ; then
      echo -e "${start_process_line}\nПроизошла ошибка при установке gnupg. (3.1/${commands})\n${end_process_line}"
      exit 2
    fi

    #3.2
    if ! sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys BA6932366A755776 ; then
      echo -e "${start_process_line}\nПроизошла ошибка при добавлении ключа репозитория. (3.2/${commands})\n${end_process_line}"
      exit 2
    fi

    #3.3
    if ! sudo add-apt-repository -s "deb https://ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu focal main" ; then
      echo -e "${start_process_line}\nПроизошла ошибка при добавлении репозитория. (3.3/${commands})\n${end_process_line}"
      exit 2
    fi

    #3.4
    sudo tee /etc/apt/preferences.d/10deadsnakes-ppa >/dev/null <<EOF
Package: *
Pin: release o=LP-PPA-deadsnakes
Pin-Priority: 100
EOF
    if $? -ne 0 ; then
      echo -e "${start_process_line}\nПроизошла ошибка при добавлении приоритета репозитория. (3.4/${commands})\n${end_process_line}"
      exit 2
    fi
    ;;
  *)
    #3
    if ! sudo add-apt-repository -y ppa:deadsnakes/ppa ; then
      echo -e "${start_process_line}\nПроизошла ошибка при добавлении репозитория. (3/${commands})\n${end_process_line}"
      exit 2
    fi
    ;;
esac

#4
if ! sudo apt update ; then
  echo -e "${start_process_line}\nПроизошла ошибка при обновлении списка пакетов. (4/${commands})\n${end_process_line}"
  exit 2
fi


clear
echo -e "$start_process_line\nУстанавливаю необходимые пакеты...\n$end_process_line"


#5
if ! sudo apt install -y curl ; then
  echo -e "${start_process_line}\nПроизошла ошибка при установке Curl. (5/${commands})\n${end_process_line}"
  exit 2
fi

#6
if ! sudo apt install -y unzip ; then
  echo -e "${start_process_line}\nПроизошла ошибка при установке Unzip. (6/${commands})\n${end_process_line}"
  exit 2
fi

#6.1
if grep -q '^[#[:space:]]*precedence[[:space:]]*::ffff:0:0/96' /etc/gai.conf; then
    if ! sudo sed -i 's|^[#[:space:]]*precedence[[:space:]]*::ffff:0:0/96.*|precedence ::ffff:0:0/96 100|' /etc/gai.conf; then
        echo -e "${start_process_line}\nПроизошла ошибка при настройке gai.conf. (6.1/${commands})\n${end_process_line}"
        exit 2
    fi
elif ! grep -qxF 'precedence ::ffff:0:0/96 100' /etc/gai.conf; then
    if ! echo 'precedence ::ffff:0:0/96 100' | sudo tee -a /etc/gai.conf >/dev/null; then
        echo -e "${start_process_line}\nПроизошла ошибка при настройке gai.conf. (6.1/${commands})\n${end_process_line}"
        exit 2
    fi
fi

clear
echo -e "$start_process_line\nУстанавливаю Python...\n$end_process_line"


#7
case $distro_version in
  "24.04" | "24.10")
    if ! sudo apt install -y python3.12 python3.12-dev python3.12-gdbm python3.12-venv ; then
      echo -e "${start_process_line}\nПроизошла ошибка при установке Python. (7/${commands})\n${end_process_line}"
      exit 2
    fi
    ;;
  *)
    if ! sudo apt install -y python3.11 python3.11-dev python3.11-gdbm python3.11-venv ; then
      echo -e "${start_process_line}\nПроизошла ошибка при установке Python. (7/${commands})\n${end_process_line}"
      exit 2
    fi
    ;;
esac

clear
echo -e "$start_process_line\nСоздаю пользователя и устанавливаю/обновляю Pip...\n$end_process_line"

#8
if id "$username" &>/dev/null; then
    echo -e "${CYAN}Пользователь $username уже существует, пропускаем создание.${RESET}"
else
    if ! sudo useradd -m "$username"; then
        echo -e "${start_process_line}\nПроизошла ошибка при создании пользователя. (8/${commands})\n${end_process_line}"
        exit 2
    fi
fi

#9
case $distro_version in
  "24.04" | "24.10")
    if ! sudo -u $username python3.12 -m venv /home/$username/pyvenv ; then
      echo -e "${start_process_line}\nПроизошла ошибка при создании виртуального окружения. (9/${commands})\n${end_process_line}"
      exit 2
    fi
    ;;
  *)
    if ! sudo -u $username python3.11 -m venv /home/$username/pyvenv ; then
      echo -e "${start_process_line}\nПроизошла ошибка при создании виртуального окружения. (9/${commands})\n${end_process_line}"
      exit 2
    fi
    ;;
esac

#10
# Важно: eunsurepip стоить запускать от root, иначе будет ошибка на некоторых версиях ОС (например, Debian 11, Debian 12, Ubuntu 20.04, Ubuntu 24.04)
if ! sudo /home/$username/pyvenv/bin/python -m ensurepip --upgrade ; then
  echo -e "${start_process_line}\nПроизошла ошибка при установке Pip. (10/${commands})\n${end_process_line}"
  exit 2
fi

#11
if ! sudo -u $username /home/$username/pyvenv/bin/python -m pip install --upgrade pip ; then
  echo -e "${start_process_line}\nПроизошла ошибка при обновлении Pip. (11/${commands})\n${end_process_line}"
  exit 2
fi

#12
if ! sudo chown -hR $username:$username /home/$username/pyvenv ; then
  echo -e "${start_process_line}\nПроизошла ошибка при изменении владельца виртуального окружения. (12/${commands})\n${end_process_line}"
  exit 2
fi


clear
echo -e "$start_process_line\nУстанавливаю FunPayNEXT...\n$end_process_line"


# Download one tagged revision, commit, or the main branch of the fork.
source_ref="${FUNPAYNEXT_REF:-main}"
if [[ ! "$source_ref" =~ ^[a-zA-Z0-9._-]+$ ]]; then
  echo "Недопустимый FUNPAYNEXT_REF: $source_ref"
  exit 2
fi
install_tmp=$(mktemp -d) || exit 2
trap 'rm -rf -- "$install_tmp"' EXIT

if ! curl -fLsS --retry 3 "https://api.github.com/repos/xelawave/FunPayNEXT/zipball/$source_ref" \
    -o "$install_tmp/source.zip" ||
   ! unzip -q "$install_tmp/source.zip" -d "$install_tmp/source"; then
  echo "Не удалось загрузить FunPayNEXT ($source_ref)."
  exit 2
fi

source_dirs=("$install_tmp"/source/*/)
app_dir="/home/$username/funpaynext"
if [[ ${#source_dirs[@]} -ne 1 || ! -f "${source_dirs[0]}funpaynext.py" ]]; then
  echo "В архиве нет файлов FunPayNEXT. Проверьте FUNPAYNEXT_REF."
  exit 2
fi
if ! sudo mkdir -p -- "$app_dir" ||
   ! sudo cp -r -- "${source_dirs[0]}." "$app_dir/"; then
  echo "Не удалось установить файлы FunPayNEXT."
  exit 2
fi


#19
if ! sudo chown -hR -- "$username:$username" "$app_dir"; then
  echo -e "${start_process_line}\nПроизошла ошибка при изменении владельца файлов. (19/${commands})\n${end_process_line}"
  exit 2
fi

#20
if ! sudo -u $username /home/$username/pyvenv/bin/pip install -U -r /home/$username/funpaynext/requirements.txt ; then
  echo -e "${start_process_line}\nПроизошла ошибка при установке необходимых Py-пакетов. (20/${commands})\n${end_process_line}"
  exit 2
fi


clear
echo -e "$start_process_line\nСоздаю ссылку на файл фонового процесса...\n$end_process_line"


#21
if ! sudo ln -sf /home/$username/funpaynext/funpaynext@.service /etc/systemd/system/funpaynext@.service ; then
  echo -e "${start_process_line}\nПроизошла ошибка при создании ссылки на файл фонового процесса. (21/${commands})\n${end_process_line}"
  exit 2
fi


clear
echo -e "$start_process_line\nНастраиваю кодировку сервера...\n$end_process_line"


#22
case $distro_version in
  "11" | "12")
    if ! sudo apt install -y locales locales-all ; then
      echo -e "${start_process_line}\nПроизошла ошибка при установке локализаций. (22/${commands})\n${end_process_line}"
      exit 2
    fi
    ;;
  *)
    if ! sudo apt install -y language-pack-en ; then
      echo -e "${start_process_line}\nПроизошла ошибка при установке языковых пакетов. (22/${commands})\n${end_process_line}"
      exit 2
    fi
    ;;
esac


clear
echo -e "$logo"
echo -e '\n\n\e[1;91m * GitHub \e[1;96mgithub.com/xelawave/FunPayNEXT\e[0m'

echo -e "\n\n\e[1;92m################################################################################"
echo -e "Установка завершена."
echo -e "Запускаю первичную настройку..."
echo -e "################################################################################\e[0m"
sleep 3
clear

CONFIG_FILE="$app_dir/configs/_main.cfg"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Файл конфигурации не найден. Запускаем первичную настройку..."
    sudo -u "$username" LANG=en_US.utf8 "/home/$username/pyvenv/bin/python" "$app_dir/main.py"
else
    echo -ne "\n${RED}Файл конфигурации найден.${RESET} Хотите добавить Telegram прокси? [y/n]:  "
    read edit_config
    case "$edit_config" in
        [yY]|[yY][eE][sS])
            echo -ne "${CYAN}Запускаем редактирование Telegram прокси...${RESET}\n\n"
            sudo -u "$username" LANG=en_US.utf8 "/home/$username/pyvenv/bin/python" -W ignore::SyntaxWarning "$app_dir/setup_telegram_proxy.py"
            ;;
        *)
            echo -ne "${CYAN}Редактирование пропущено.${RESET}"
            ;;
    esac

fi

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Первичная настройка не завершена."
  exit 2
fi

if ! sudo systemctl daemon-reload || ! sudo systemctl restart "funpaynext@$username.service"; then
  echo "Не удалось запустить службу FunPayNEXT."
  exit 2
fi

clear
echo -e "$logo"
echo -e '\n\n\e[1;91m * GitHub \e[1;96mgithub.com/xelawave/FunPayNEXT\e[0m'

echo -e "\n\n\e[1;92m################################################################################"
echo -e "${RED}!СДЕЛАЙ СКРИНШОТ!${CYAN}!СДЕЛАЙ СКРИНШОТ!${RED}!СДЕЛАЙ СКРИНШОТ!${CYAN}!СДЕЛАЙ СКРИНШОТ!"
echo -e "\nГотово!"
echo -e "FunPayNEXT запущен как фоновый процесс!"
echo -e "Теперь напиши своему Telegram-боту."
echo -e "\n\e[1;92mДля остановки FunPayNEXT используй команду \e[93msudo systemctl stop funpaynext@${username}\e[1;92m"
echo -e "Для запуска FunPayNEXT используй команду \e[93msudo systemctl start funpaynext@${username}\e[1;92m"
echo -e "Для перезапуска FunPayNEXT используй команду \e[93msudo systemctl restart funpaynext@${username}\e[1;92m"
echo -e "Для просмотра логов используй команду \e[93msudo systemctl status funpaynext@${username} -n100\e[1;92m"
echo -e "Для добавления FunPayNEXT в автозагрузку используй команду \e[93msudo systemctl enable funpaynext@${username}\e[1;92m"
echo -e "${RED}* Перед добавлением FunPayNEXT в автозагрузку убедись, что твой бот работает корректно.\e[1;92m"
echo -e "################################################################################\e[0m"

echo -ne "\n\n${CYAN}Сделал скриншот? ${PURPLE_LIGHT}Тогда нажми Enter, чтобы продолжить.${RESET}"
read
clear
