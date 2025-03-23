import requests
import json

API_URL = "http://127.0.0.1:8003"


def path_builder(endpoint: str):
    return API_URL + "/v1" + endpoint


def print_request_info(url, data):
    """
    Prints the requested URL and the JSON data in a formatted way.

    Parameters:
        url (str): The requested URL.
        data (dict): The data to be printed in JSON format.
    """
    print("Requested URL:", url)
    print(json.dumps(data, indent=4))
    print("\n")


def signup(data: dict):
    try:
        url = path_builder("/signup")
        res = requests.post(url, json=data)
        data = res.json()
        print("users added")
        print_request_info(url, data)
        return data
    except Exception as identifier:
        print(identifier)


def signin(data: dict):
    try:
        url = path_builder("/signin")
        res = requests.post(url, json=data)
        data = res.json()
        print("users login")
        print_request_info(url, data)
        return data
    except Exception as identifier:
        print(identifier)


def token(data: dict):
    try:
        url = path_builder("/token")
        res = requests.post(url, json=data)
        data = res.json()
        print("refresh access token")
        print_request_info(url, data)
        return data
    except Exception as identifier:
        print(identifier)


def forgot(data: dict):
    try:
        url = path_builder("/forgot")
        res = requests.post(url, json=data)
        print(res.headers)
        if res.is_redirect:
            redirect_url = res.headers.get("Location")
            print("Redirect URL:", redirect_url)
        data = res.json()
        print_request_info(url, data)
        return data
    except Exception as identifier:
        print(identifier)


def delete(id: int):
    url = path_builder(f"/users/{id}")
    res = requests.delete(url, json=data)
    data = res.json()
    print_request_info(url, data)
    return data


creadentials = {
    "username": "santo",
    "name": "Santo",
    "email": "inbox.santo@hotmail.com",
    "password": "Santo1234",
}
forgot_creadentials = {"email": "inbox.santo@hotmail.com"}
reset_creadentials = {"email": "inbox.santo@hotmail.com", "password": "santo@1234"}


signup(creadentials)
user = signin(creadentials)
# token(user)
# forgot(forgot_creadentials)
# delete(user["id"])
