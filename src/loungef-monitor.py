import os
import stat
import sys
import time
import copy
import logging
from pathlib import Path
from dotenv import load_dotenv
import pymongo

# The class that monitors files in a given directory.
# 
# It read the information of the files in a directory (name, path, creation
# date/time, modification date/time and size) and notify a MongoDB table if
# there are new, removed or changed files.
class LoungeFMonitor(object):
    def __init__(self, p_path_to_monitor, p_path_to_archive, p_interval = 5, p_archive_after = 432000):
        self.path            = str(Path(p_path_to_monitor))
        self.archivePath     = str(Path(p_path_to_archive))
        self.monitorInterval = int(p_interval or 5)
        self.archiveAfter    = int(p_archive_after or 432000)
        assert os.path.exists(self.path), "Invalid path to monitor: %s" % self.path
        assert os.path.exists(self.archivePath), "Invalid path to archive: %s" % self.archivePath
        assert (self.monitorInterval >= 3), "Invalid value for LF_INTERVAL: %s and must be >= 3" % p_interval
        assert (self.archiveAfter >= 10), "Invalid value for LF_ARCHIVE_AFTER: %s and must be >= 10" % p_archive_after

        self.list            = self.lfScanDir(self.path)
        self.changed         = []

    def lfScanDir(self, p_path):
        logging.debug("lfScanDir method started.")
        ret = {}

        # os.scandir() (>= python 3.5) is used with 'with' context manager.
        # Context manager closes the iterator and frees up resources
        # automatically after the iterator has been finished.
        with os.scandir(p_path) as entries:
            for entry in entries:
                ret.update({str(entry.inode()):
                                {
                                    'inode': entry.inode(),
                                    'name': entry.name,
                                    'path': str(Path(entry.path).parent),
                                    'ctime': os.path.getctime(entry),
                                    'mtime': os.path.getmtime(entry),
                                    'size': os.path.getsize(entry),
                                    'archived': False
                                }
                            }
                )

        logging.debug('lfScanDir ret: %s', ret)
        logging.debug("lfScanDir method ended.")
        return ret

    def compareFileLists(self, p_d1, p_d2):
        logging.debug("compareFileLists method started.")
        ret = {}

        # There is some either new or gone inode?
        uniqKeyDiff = p_d1.keys() ^ p_d2.keys()

        if len(uniqKeyDiff) == 0:
            logging.info("No inode changes detected.")

            for inode, attrs in p_d1.items():
                logging.debug("Check if some attribute from both lists has changed.")
                uniqDiff = attrs.items() ^ p_d2[inode].items()

                if len(uniqDiff) == 0:
                    logging.info("No changes neither on file list or its attributes.")
                else:
                    logging.info('Detected change in file [%s], inode [%s].', p_d1[inode]['name'], inode)
                    ret.update({inode: p_d1[inode]})
        else:
            logging.info("Some inode changed!")

            for diffInode in uniqKeyDiff:
                logging.info('Verifying inode [%s].', diffInode)

                if diffInode in p_d1:
                    logging.info('A new file arrived.')
                    logging.debug('New file arrived. Found inode [%s] on p_d1.', diffInode)
                    ret.update({diffInode: p_d1[diffInode]})
                else:
                    logging.info('A file might be removed.')
                    logging.debug('Removed file. Found inode [%s] on p_d2.', diffInode)
                    ret.update({diffInode: p_d2[diffInode]})

        finalret = copy.deepcopy(ret)
        logging.debug("compareFileLists method ended.")
        return finalret

    def check(self):
        logging.debug("check method started.")
        newlist      = self.lfScanDir(self.path)
        self.archiveFiles(newlist)
        self.changed = self.compareFileLists(newlist, self.list)
        self.list    = copy.deepcopy(newlist)
        logging.debug("check method ended.")

    def archiveFiles(self, p_list):
        logging.debug("archiveFiles method started.")
        ret      = False
        now      = time.time()

        for inodeID, inodeItem in p_list.items():
            if ((now - inodeItem['mtime']) > self.archiveAfter):
                dirsep      = '/' # TODO: Fix hardcoded directory separator.

                source      = Path(inodeItem['path'] + dirsep + inodeItem['name'])
                logging.debug('source: %s', source)

                destination = Path(self.archivePath + dirsep + inodeItem['name'])
                logging.debug('destination: %s', destination)

                source.replace(destination)
                logging.info('Moved %s to %s.', source, destination)

                inodeItem['archived'] = True
                inodeItem['path'] = self.archivePath

        # logging.debug('Final newlist: %s', p_list)
        logging.debug("archiveFiles method ended.")
        ret    = True
        return ret

    def sendDataToDB(self):
        logging.debug("sendDataToDB method started.")
        ret    = False

        # Sending data for MongoDB Atlas service.
        # Standard port is 27017
        client     = pymongo.MongoClient(os.getenv("LF_MONGO_HOST"))
        db         = client[os.getenv("LF_MONGO_DB")]
        dirhistory = db[os.getenv("LF_MONGO_CL")]
        logging.debug("Connection to MongoDB occurred successfuly.")

        for inodeID, inodeInfo in self.changed.items():
            docentry = dirhistory.insert_one(inodeInfo).inserted_id
            logging.info('INode [%s] appended as MongoDB object [%s].', inodeID, docentry)
            tmp = dirhistory.find_one({"_id": docentry})

            if tmp != None:
                logging.debug('object created: %s', tmp)
            else:
                logging.error("Error while creating the object!")

        ret = True
        logging.debug("sendDataToDB method ended.")
        return ret

    def watch(self):
        logging.debug("watch method started.")

        try:
            while True:
                time.sleep(self.monitorInterval)
                self.check()
                ci = len(self.changed)

                if ci > 0:
                    if self.sendDataToDB():
                        self.changed.clear()
                    else:
                        logging.critical("Something very bad is happening! Records might not be sent for MongoDB.")
                        logging.critical("Finishing program. Look for more information on logs.")
                        break;

        except KeyboardInterrupt:
            logging.warning("Finishing the program after keyboard interrupt.")
        except:
            logging.critical('Unexpected error: %s', sys.exc_info()[0])
            raise


if __name__ == '__main__':
    dirsep   = '/' # TODO: Fix hardcoded directory separator.
    env_path = Path(os.getenv("LF_APPHOME") + dirsep + 'config' + dirsep) / '.env'
    load_dotenv(dotenv_path=env_path)
    logging.basicConfig(filename=Path(os.getenv("LF_LOGFILE")), format='%(asctime)s:%(levelname)s:%(message)s', level=logging.DEBUG)
    logging.info('LoungeFMonitor started!')
    logging.debug('Directory to Monitor: %s', os.getenv("LF_MONITOR_DIR"))
    logging.debug('Directory to Archive: %s', os.getenv("LF_ARCHIVE_DIR"))
    logging.debug('Polling interval....: %s', os.getenv("LF_INTERVAL"))
    logging.debug('Archive after.......: %s', os.getenv("LF_ARCHIVE_AFTER"))

    monitor = LoungeFMonitor(os.getenv("LF_MONITOR_DIR"),
                               os.getenv("LF_ARCHIVE_DIR"),
                               os.getenv("LF_INTERVAL"),
                               os.getenv("LF_ARCHIVE_AFTER"))

    monitor.watch()
    logging.warning('LoungeFMonitor finished!')
