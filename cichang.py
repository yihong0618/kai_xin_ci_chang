import argparse
import base64
import hashlib
import io
import json
import os
import zipfile

import pandas as pd
import requests
from rich import print

HJ_APPKEY = "45fd17e02003d89bee7f046bb494de13"
LOGIN_URL = "https://pass.hujiang.com/Handler/UCenter.json?action=Login&isapp=true&language=zh_CN&password={password}&timezone=8&user_domain=hj&username={user_name}"
COVERT_URL = "https://pass-cdn.hjapi.com/v1.1/access_token/convert"
MY_BOOKS_URL = (
    "https://cichang.hjapi.com/v3/user/me/book_study?type=4&start=0&limit=1000"
)
STUDY_BOOK_INFO_URL = "https://cichang.hjapi.com/v3/user/me/book_study/{book_id}"
STUDY_BOOK_RESOURCE_INFO_URL = (
    "https://cichang.hjapi.com/v3/user/me/book/{book_id}/resource"
)
TO_SAVE_FILES_DICT = {
    "sentAudioResource": "sentences",
    "wordAudioResource": "words",
    "textResource": "files",
}
FILES_ROOT = "FILES_OUT"
DEFAULT_WORD_FILE_ROOT = os.path.join(FILES_ROOT, "files", "word.txt")
DEFAULT_TO_CSV_NAME = "my_learning_book.csv"

# added in 2023.06.08
XIAOD_LIST_URL = "https://vocablist.hjapi.com/notebook/notebooklist?lastSyncDate=2000-01-01T00%3A00%3A00.000&lastSyncVer=0&syncVer=1"
XIAOD_ONE_NOTE_URL = "https://vocablist.hjapi.com/notebook/notewords?lastSyncDate=2000-01-01T00%3A00%3A00.000&lastSyncVer=0&nbookid={nbook_id}&oldnbookid=0&syncVer=1"


def md5_encode(string):
    m = hashlib.md5()
    m.update(string.encode())
    return m.hexdigest()


def decode(s):
    try:
        bytes = bytearray(base64.b64decode(s))
        for i in range(len(bytes)):
            bytes[i] = 255 ^ bytes[i]
        s = bytes.decode("utf8")
    except:
        pass
    return s


def get_zip_password(version_str):
    b = [ord(i) for i in version_str]
    b = [i ^ -1 for i in b]
    return str(base64.b64encode(bytes(x % 256 for x in b)))[2:-1]


def get_learning_books_info(s):
    r = s.get(MY_BOOKS_URL)
    if not r.ok:
        raise Exception("Can not get books info from hujiang")
    return r.json()["data"]["result"]


def get_book_resource_info(s, book_id):
    r = s.get(STUDY_BOOK_RESOURCE_INFO_URL.format(book_id=book_id))
    if not r.ok:
        raise Exception("Can not get this book resource from hujiang")
    return r.json()["data"]


def download_zip_files(file_root_url, zip_pass, file_dir):
    r = requests.get(file_root_url)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(file_dir, pwd=bytes(zip_pass, "utf-8"))


####### XIAOD #######
def get_xiaod_notes_dict(s):
    r = s.get(XIAOD_LIST_URL)
    if not r.ok:
        raise Exception("Can not note books info from hujiang")
    d = {}
    node_list = r.json()["data"]["noteList"]
    for n in node_list:
        d[n["nbookId"]] = n["nbookName"]
    return d


def get_xiaod_words(s, nbook_id):
    r = s.get(XIAOD_ONE_NOTE_URL.format(nbook_id=nbook_id))
    if not r.ok:
        raise Exception(f"Can not get words for nbook_id: {nbook_id}")
    return r.json()


def login(user_name, password):
    s = requests.Session()
    password_md5 = md5_encode(password)
    r = s.get(LOGIN_URL.format(user_name=user_name, password=password_md5))
    if not r.ok:
        raise Exception(f"Someting is wrong to login -- {r.text}")
    club_auth_cookie = r.json()["Data"]["Cookie"]
    data = {"club_auth_cookie": club_auth_cookie}
    headers = {"hj_appkey": HJ_APPKEY, "Content-Type": "application/json"}
    # real login to get real token
    r = s.post(COVERT_URL, headers=headers, data=json.dumps(data))
    if not r.ok:
        raise Exception(f"Get real token failed -- {r.text}")
    access_token = r.json()["data"]["access_token"]
    headers["Access-Token"] = access_token
    s.headers = headers
    return s


def parse_book_to_pandas(file_root=DEFAULT_WORD_FILE_ROOT):
    with open(file_root) as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df = df[
        [
            "ItemID",
            "WordID",
            "Word",
            "WordDef",
            "SentenceID",
            "Sentence",
            "SentenceDef",
            "UnitID",
        ]
    ]
    df["WordDef"] = df["WordDef"].apply(decode)
    df["Sentence"] = df["Sentence"].apply(decode)
    df["SentenceDef"] = df["SentenceDef"].apply(decode)
    df["WordDef"] = df["WordDef"].apply(decode)
    return df


def make_ci_chang_book(s):
    learning_books_info = get_learning_books_info(s)
    print("your learning book info is", learning_books_info)

    if not learning_books_info:
        print("No learning book for now")
    # only get the first book, you can DIY here
    now_learning_book_id = learning_books_info[0]["book"]["id"]
    book_resource_data = get_book_resource_info(s, now_learning_book_id)
    for k, v in book_resource_data.items():
        if k not in TO_SAVE_FILES_DICT:
            continue
        version = v.get("version")
        url = v.get("url")
        if not version:
            try:
                version = url.split("/")[-1].split(".")[0]
            except Exception as e:
                print(f"Get zip version failed with error {str(e)}")
                raise
        zip_pass = get_zip_password(str(version))
        file_dir = os.path.join("FILES_OUT", TO_SAVE_FILES_DICT.get(k))
        if not os.path.exists(file_dir):
            os.mkdir(file_dir)
        try:
            print(f"Downloading {url} please wait")
            download_zip_files(url, zip_pass, file_dir)
        except Exception as e:
            print(str(e))
            pass
    df = parse_book_to_pandas()
    df.to_csv(DEFAULT_TO_CSV_NAME)


def make_xiaod_note(s):
    note_dict = get_xiaod_notes_dict(s)
    for k, v in note_dict.items():
        data = get_xiaod_words(s, k)
        word_list = data["data"]["wordList"] 
        if not word_list:
            print(f"No data in {v}")
            continue
        df = pd.DataFrame(word_list)
        df = df[
            ["word", "wordId", "definition", "clientDateAdded", "clientDateUpdated"]
        ]
        df.to_csv(f"{v}.csv")


def main(user_name, password, is_xiaod=False):
    s = login(user_name, password)
    if is_xiaod:
        make_xiaod_note(s)
    else:
        make_ci_chang_book(s)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("user_name", help="hujiang_user_name")
    parser.add_argument("password", help="hujiang_password")
    parser.add_argument(
        "-xd",
        "--xiaod",
        dest="is_xiaod",
        action="store_true",
        help="if is_xiaod",
    )
    options = parser.parse_args()
    main(options.user_name, options.password, options.is_xiaod)
