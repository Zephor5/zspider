# coding=utf-8

__author__ = "zephor"


def get_ip(inner=True):
    """
    get local ip addr
       default get inner ip address, set `inner` to False to
          get public ip if exists, or it will return the first ip found
       it returns 'localhost' when failed
    """
    import re

    ip_list = []

    def is_inner_ip(x):
        ip_lst = x.split(".")
        if len(ip_lst) != 4:
            return False
        if ip_lst[0] == "10":
            return True
        if ip_lst[:2] == ["192", "168"]:
            return True
        if ip_lst[0] == "172" and 16 <= int(ip_lst[1]) <= 31:
            return True
        return False

    try:
        # noinspection PyUnresolvedReferences
        from netifaces import interfaces, ifaddresses, AF_INET

        for interface in interfaces():
            try:
                links = ifaddresses(interface)[AF_INET]
            except KeyError:
                continue
            for link in links:
                ip_list.append(link["addr"])
    except ImportError:
        try:
            import subprocess

            _null = open("/dev/null", "a")
            ip_list = (
                subprocess.Popen(
                    "/sbin/ifconfig|grep 'inet '|awk '{print $2}'",
                    stdout=subprocess.PIPE,
                    stderr=_null,
                    shell=True,
                )
                .communicate()[0]
                .split(b"\n")
            )
            _null.close()
            ip_list = [
                re.sub(r"^.*?(\d+\.\d+\.\d+\.\d+).*$", r"\1", itm) for itm in ip_list
            ]
        except Exception:
            ip_list = []
    ip_list = list(
        filter(lambda x: re.match(r"^(\d+\.){3}\d+$", x) and x != "127.0.0.1", ip_list)
    )
    if not ip_list:
        return "localhost"
    elif len(ip_list) == 1:
        return ip_list[0]
    else:
        for ip in ip_list:
            if inner == is_inner_ip(ip):
                return ip
        return ip_list[0]


if __name__ == "__main__":
    print("inner ip:", get_ip())
    print("pub ip:", get_ip(False))
