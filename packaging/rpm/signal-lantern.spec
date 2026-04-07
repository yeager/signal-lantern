Name:           signal-lantern
Version:        0.1.0
Release:        1%{?dist}
Summary:        GTK desktop helper that explains common Linux system problems
License:        MIT
URL:            https://github.com/openclaw/signal-lantern
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-pip
BuildRequires:  python3-wheel
BuildRequires:  gettext
BuildRequires:  desktop-file-utils

Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       iproute
Requires:       iputils
Recommends:     NetworkManager
Recommends:     gnome-control-center
Recommends:     gnome-system-monitor
Recommends:     baobab

%description
Signal Lantern watches for common network and system problems on Linux
desktops, explains them in plain English, and exposes technical details
when you want them. It checks connectivity, Wi-Fi, DNS, CPU, memory,
disk, battery, and more.

%prep
%autosetup -n %{name}-%{version}

%build
%pyproject_wheel

# Compile gettext catalogs
for po in po/*.po; do
    lang=$(basename "$po" .po)
    mkdir -p locale/$lang/LC_MESSAGES
    msgfmt -o locale/$lang/LC_MESSAGES/signal-lantern.mo "$po"
done

%install
%pyproject_install
%pyproject_save_files signallantern

# Desktop file
install -Dm644 data/io.github.signallantern.desktop \
    %{buildroot}%{_datadir}/applications/io.github.signallantern.desktop
desktop-file-validate %{buildroot}%{_datadir}/applications/io.github.signallantern.desktop

# Icon
install -Dm644 data/io.github.signallantern.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/io.github.signallantern.svg

# Locale files
for mo in locale/*/LC_MESSAGES/signal-lantern.mo; do
    lang=$(echo "$mo" | cut -d/ -f2)
    install -Dm644 "$mo" \
        %{buildroot}%{_datadir}/locale/$lang/LC_MESSAGES/signal-lantern.mo
done

%find_lang signal-lantern

%files -f %{pyproject_files} -f signal-lantern.lang
%license debian/copyright
%doc README.md
%{_bindir}/signal-lantern
%{_datadir}/applications/io.github.signallantern.desktop
%{_datadir}/icons/hicolor/scalable/apps/io.github.signallantern.svg
