Name:           signal-lantern
Version:        0.1.0
Release:        1%{?dist}
Summary:        GTK 4 desktop helper for common Linux system problems
License:        MIT
URL:            https://github.com/yeager/signal-lantern
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  desktop-file-utils
BuildRequires:  gettext
BuildRequires:  pyproject-rpm-macros
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools

Requires:       gtk4
Requires:       iproute
Requires:       iputils
Requires:       libadwaita
Requires:       NetworkManager
Requires:       python3-gobject

%description
Signal Lantern is a GTK 4 and libadwaita desktop helper that watches common
Linux network and system problems, explains them in plain language, and offers
simple steps to help the user recover.

%prep
%autosetup -n %{name}-%{version}

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel
chmod +x scripts/compile-translations.sh
./scripts/compile-translations.sh

desktop-file-validate data/io.github.signallantern.desktop

%install
%pyproject_install
mkdir -p %{buildroot}%{_datadir}/applications
mkdir -p %{buildroot}%{_datadir}/icons/hicolor/scalable/apps
mkdir -p %{buildroot}%{_datadir}/locale
install -Dm0644 data/io.github.signallantern.desktop %{buildroot}%{_datadir}/applications/io.github.signallantern.desktop
install -Dm0644 data/io.github.signallantern.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/io.github.signallantern.svg
if [ -d locale ]; then
  find locale -mindepth 2 -maxdepth 2 -type d -name LC_MESSAGES | while read -r msgdir; do
    lang="$(basename "$(dirname "$msgdir")")"
    mkdir -p "%{buildroot}%{_datadir}/locale/${lang}/LC_MESSAGES"
    cp -a "$msgdir"/*.mo "%{buildroot}%{_datadir}/locale/${lang}/LC_MESSAGES/"
  done
fi

%check
PYTHONPATH=src python3 -m compileall src

%files
%license LICENSE*
%doc README.md ARCHITECTURE.md STATUS.md
%{_bindir}/signal-lantern
%{python3_sitelib}/signallantern/
%{python3_sitelib}/signal_lantern-*.dist-info/
%{_datadir}/applications/io.github.signallantern.desktop
%{_datadir}/icons/hicolor/scalable/apps/io.github.signallantern.svg
%{_datadir}/locale/*/LC_MESSAGES/signal-lantern.mo

%changelog
* Tue Apr 07 2026 Daniel Nylander <daniel@danielnylander.se> - 0.1.0-1
- Initial RPM package
