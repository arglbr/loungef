# DEPRECATED

![no-maintenance-intended](https://img.shields.io/maintenance/no/2019?style=plastic)

# loungef

> Deprecated, obsolete & archived.
> 
> This was part of an interview process I've made at 2019, and I keep it here just for historical purposes.

All artifacts for RHEA test.

Requirements
---------------------
* Internet;
* Linux or MacOS box;
* Python (version >= 3.6);
* python-pip;

Setup
---------------------
There are many ways to setup a Python environment for installation. Here I am using the *virtualenvironment* approach. Note: this package does not support legacy Python and will only work with Python 3.x, where *x >= 3.6* (might work on 3.5 but I did not test).

Get the project's code:

```
$ git clone 'https://github.com/arglbr/loungef.git'
$ cd loungef
```

Before start, we need to assure that the variable LF_APPHOME is correctly set. It points to the project home directory, so please review it first:

```
# on bin/lounge, line 3:
export LF_APPHOME=${HOME}/loungef # <- change for the home on the host running the project.
```

The following will setup a virtualenvironment, activate it, setup some environment variables and generates a valid .env configuration:

```
$ bin/loungef --install
```
After the install, you must check and review each of the options presented in the config/.env file. An important thing is that the metadata is sent to a MongoDB in the cloud (MongoDB Atlas service). Is just for this test purpouse, but if you do not agree, the configuration can be changed for another MongoDB instance that is running. As mentioned in this file, the connection string must provide a username with access rights to the informed collection.
```
LF_MONGO_HOST=mongodb+srv://mongodb-connection-string
LF_MONGO_DB=mongodb-database
LF_MONGO_CL=mongodb-collection
```

With the .env file reviewed you can put up the daemon that monitors for directory changes.
```
$ bin/loungef --start 
```
At this point, the directory informed for the ``LF_MONITOR_DIR`` variable on the config/.env file is being watched and any changes will be logged on the logfile informed for the ``LF_LOGFILE`` and on the MongoDB configured. The changes are verified each N seconds, where N is the value configured for the variable ``LF_INTERVAL``.

This daemon also archive files. A file needs to be archived after X seconds inside the monitored directory, where X is configured on the variable ``LF_ARCHIVE_AFTER``. The directory that will hold the archived files is defined at ``LF_ARCHIVE_DIR``.

Now the REST API. First, we need to put it up firing:
```
$ bin/loungef --apistart
```
Your API root will be:
```
http://{host}:9832/loungef-api/
```
Use the hostname or IP of the host that is serving the API, like: `` http://127.0.0.1:9832/loungef-api/``

This API has two endpoints:
* [GET] http://{host}:9832/loungef-api/files/archived: show the list of the files that has been archived.
* [GET] http://{host}:9832/loungef-api/files/available: show the list of files that is available and is not archived yet.

To stop playing with this project, do:
```
$ bin/loungef --apistop 
$ bin/loungef --stop
```

Why 'LoungeF'? What name is this?
---------------------
I tried something like 'Lounge for Files'. But I agree that it was a terrible idea.

License information
---------------------

The code is a free software: do what you want, but please, I cannot receive any accountability if this software causes some damage.