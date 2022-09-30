import moltin
from tgbot import get_access_token


def main():
        moltin.get_flows(get_access_token())


if __name__ == '__main__':
    main()