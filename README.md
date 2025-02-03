# hlxkit
Save images of x.com users.  
Saves all IDs of the specified user to save recursively.  

## Install 
```bash
pip -r install requirements.txt
```

## Using
Writes IDs line by line to a file called `xids`.  
example :
```bash:xids
userid1
userid2
```

A login session is required, so enter your ID.  
This will be written in the second `.env` file.  
example : 
```bash:.env
TWITTER_USERNAME=userid
TWITTER_EMAIL=example@mail.com
TWITTER_PASSWORD=password
SAVE_BASE_FOLDER=/your/download/dir
RETRY_LIMIT=5
RETRY_DELAY=900
```

Give the script execute permission.
```bash
chmod +x xmkt.py
```
done.

## exec
```bash
./xmkt.py
```
