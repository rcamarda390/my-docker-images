# pcre2-security.spec: UBI10-native PCRE2 runtime security replacement.
Name:           pcre2
Version:        10.49
Release:        1.rcamarda1%{?dist}
Summary:        Perl-compatible regular expression library
License:        BSD-3-Clause
URL:            https://github.com/PCRE2Project/pcre2
Source0:        pcre2-%{version}.tar.gz
BuildRequires:  gcc
BuildRequires:  make
Requires:       %{name}-syntax = %{version}-%{release}

%description
PCRE2 8-bit runtime built on UBI10 from the checksum-verified upstream release.
Replaces the distro runtime with the same libpcre2-8.so.0 and libpcre2-posix.so.3 ABIs.

%package syntax
Summary:        Documentation for PCRE2 regular expressions
BuildArch:      noarch

%description syntax
Updated regular-expression syntax documentation from the same PCRE2 source.

%prep
%autosetup -n pcre2-%{version}

%build
# Keep UBI10's unversioned exported ABI; retain JIT and Unicode support.
%configure --enable-jit --enable-unicode --disable-static --disable-symvers
%make_build

%check
# Includes upstream DFA, invalid UTF, copied-subject and JIT-stack regressions.
%make_build check

%install
# UBI10's pcre2 RPM is the 8-bit runtime. Do not add development files or tools.
install -d %{buildroot}%{_libdir} %{buildroot}%{_mandir}/man3
install -pm755 .libs/libpcre2-8.so.0.* %{buildroot}%{_libdir}/
ln -s "$(basename .libs/libpcre2-8.so.0.*)" %{buildroot}%{_libdir}/libpcre2-8.so.0
install -pm755 .libs/libpcre2-posix.so.3.* %{buildroot}%{_libdir}/
ln -s "$(basename .libs/libpcre2-posix.so.3.*)" %{buildroot}%{_libdir}/libpcre2-posix.so.3
install -pm644 doc/pcre2pattern.3 doc/pcre2syntax.3 doc/pcre2unicode.3 %{buildroot}%{_mandir}/man3/

%files
%license LICENCE.md
%{_libdir}/libpcre2-8.so.0*
%{_libdir}/libpcre2-posix.so.3*

%files syntax
%license LICENCE.md
%{_mandir}/man3/pcre2pattern.3*
%{_mandir}/man3/pcre2syntax.3*
%{_mandir}/man3/pcre2unicode.3*

%changelog
* Fri Oct 02 2026 rcamarda390 image build <rcamarda390@users.noreply.github.com> - 10.49-1.rcamarda1
- Fix seven PCRE2 CVEs in Zeus v5; retain the UBI10 runtime ABI.
