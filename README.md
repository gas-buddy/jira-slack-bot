# jira-slack-bot

To use create a lambda role in AWS and set it in the `Makefile`

Then run:

``` 
make install
. ./env/bin/activate
make build
make create
```

To push changes run

`make update`


On AWS you will need to configure the following environment variables:
```
jiraEncryptedPassword -- your jira password, encrypt with IAM
kmsEncryptedToken -- slack token, encrypt with IAM
jiraUsername -- plaintext
```
