import os
import PTN
import urllib2
import json
import shutil
import re
import datetime
import core
from core import config, sqldb, ajax, snatcher

import logging
logging = logging.getLogger(__name__)

class PostProcessing(object):

    def __init__(self):
        self.pp_conf = core.CONFIG['Postprocessing']
        self.sql = sqldb.SQL()

    def failed(self, guid, path):
        '''
        Takes str guid and str path to process failed downloads.
        Will delete path if cleanupenabled is 'true'
        Marks guid as 'Bad' in database MARKEDRESULTS
        If the guid is not from Watcher it will not mark bad or grab next result, but will still mark in MARKEDRESULTS.
        Will grab next best release if autograb is 'true'
        '''

        if guid == 'None':
            return 'Success'

        ajax.Ajax().mark_bad(guid)

        if self.pp_conf['cleanupfailed'] == 'true':
            logging.info('Deleting leftover files from failed download.')
            if os.path.ispath(path):
                try:
                    shutil.rmtree(path)
                except Exception, e:
                    logging.error('Could not delete leftover failed files.', exc_info=True)

        imdbid = self.sql.get_imdbid_from_guid(guid)
        if imdbid:
            logging.info('Post-processing {} as failed'.format(imdbid))
            try:
                if core.CONFIG['Search']['autograb'] == 'true':
                    s = snatcher.Snatcher()

                    if s.auto_grab(imdbid) == True:
                        # This ulitmately goes to an ajax response, so we can't return a bool
                        return 'Success'
                    else:
                        logging.info('Setting status of {} back to Wanted.'.format(imdbid))
                        if not self.sql.update('MOVIES', 'status', 'Wanted', imdbid=imdbid):
                            return False
                        return 'Success'
                else:
                    return 'Success'
            except Exception, e:
                logging.error('Post-processing failed.', exc_info=True)
                return 'Failed'

    def complete(self, guid, path):
        '''
        Processed completed downloads.
        Will mark guid as 'Finished' in MARKEDRESULTS
        Get imdbid from guid and marks movie as 'Finished' in MOVIES.
        If the guid is not from Watcher it searches OMDB to find the imdbid. see movie_data().
        Will rename and move is renamerenabled and moverenabled are 'true'

        Updates SEARCHRESULTS row to have correct finished date
        '''
        logging.info('Post-processing {} as complete.'.format(guid))
        imdbid = None

        # if we get a guid get the imdbid from SEARCHRESULTS. Can set imdbid None.
        if guid != 'None':
            imdbid = self.sql.get_imdbid_from_guid(guid)
            if not imdbid:
                imdbid = None

        # gets any possible information from the imdbid and path (looks at filename)
        movie_data = self.movie_data(imdbid, path, guid)

        if self.pp_conf['renamerenabled'] == 'true':
            new_name = self.renamer(movie_data)
            if new_name == False:
                return 'Fail'
            else:
                movie_data['filename'] = new_name

        if self.pp_conf['moverenabled'] == 'true':
            if self.mover(movie_data) == False:
                return 'Fail'
            else:
                if self.pp_conf['cleanupenabled'] == 'true':
                    self.cleanup(movie_data)

        # update DB tables to Finished and update MOVIES row to have finisheddate and finishedscore
        imdbid = movie_data['imdbid']
        finisheddate = movie_data['finisheddate']
        finishedscore = movie_data['finishedscore']
        try:
            if not self.sql.update('MOVIES', 'status', 'Finished', imdbid=imdbid):
                return False
            if not self.sql.update('MOVIES', 'finisheddate', finisheddate, imdbid=imdbid):
                return False
            if not self.sql.update('MOVIES', 'finishedscore', finishedscore, imdbid=imdbid):
                return False
            if not self.sql.update('SEARCHRESULTS', 'status', 'Finished', guid=guid):
                return False
            if self.sql.row_exists('MARKEDRESULTS', guid=guid) and guid != 'None':
                if not self.sql.update('MARKEDRESULTS', 'status', 'Finished', guid=guid):
                    return False

            imdbid = self.sql.get_imdbid_from_guid(guid)
            DB_STRING = {}
            DB_STRING['imdbid'] = imdbid
            DB_STRING['guid'] = guid
            DB_STRING['status'] = 'Snatched'
            if not self.sql.write('MARKEDRESULTS', DB_STRING):
                return 'Fail'

            logging.info('{} postprocessing finished.'.format(imdbid))
            return 'Success'
        except Exception, e:
            logging.error('Post-processing failed.', exc_info=True)
            return 'Fail'


    def movie_data(self, imdbid, path, guid):
        '''
        Gathers neccesary data for post-processing.
        Will search OMBD if Watcher doesn't have info for the guid.
        Returns dict as described below.
        '''

        today = str(datetime.date.today())

        # Find the biggest file in the dir. It should be safe to assume that this is the movie.
        files =  os.listdir(path)
        for file in files:
            s = 0
            abspath = os.path.join(path, file)
            size = os.path.getsize(abspath)
            if size > s:
                moviefile = file

        filename, ext = os.path.splitext(moviefile)

        '''
        This is out base dict. We declare everything here in case we can't find a value later on. We'll still have the key in the dict, so we don't need to check if a key exists every time we want to use one. This MUST match all of the options the user is able to select in Settings.
        '''
        data = {
            'title':'',
            'year':'',
            'resolution': '',
            'group':'',
            'audiocodec':'',
            'videocodec':'',
            'rated':'',
            'imdbid':'',
            'finisheddate': today,
            'finishedscore': 1000 # If we are processing a release not grabbed by Watcher we won't have a score, so 1000 is a good upper limit to use for outside processing.
        }

        # start filling out what we can
        data['filename'] = filename
        data['ext'] = ext
        data['path'] = os.path.normpath(path)

        # Parse what we can from the filename
        titledata = PTN.parse(filename)
        # this key can sometimes be a list, which is a pain to deal with later. We don't ever need it, so del
        if 'excess' in titledata:
            titledata.pop('excess')
        # Make sure this matches our key names
        if 'codec' in titledata:
            titledata['videocodec'] = titledata.pop('codec')
        if 'audio' in titledata:
            titledata['audiocodec'] = titledata.pop('audio')
        data.update(titledata)

        # if we know the imdbid we'll look it up.
        if imdbid:
            localdata = self.sql.get_movie_details(imdbid)
            if localdata:
                # this converts it to a usable dict
                localdict = dict(localdata)
                # don't want to overwrite finisheddate
                del localdict['finisheddate']
                data.update(localdict)

        # If we don't know the imdbid we'll look it up at ombd and add their info to the dict. This can happen if we are post-processing a movie that wasn't snatched by Watcher.
        else:
            title = data['title']
            year = data['year']
            search_string = 'http://www.omdbapi.com/?t={}&y={}&plot=short&r=json'.format(title, year).replace(' ', '+')

            request = urllib2.Request( search_string, headers={'User-Agent' : 'Mozilla/5.0'} )

            try:
                omdbdata = json.loads(urllib2.urlopen(request).read())
            except (SystemExit, KeyboardInterrupt):
                raise
            except Exception, e:
                logging.error('Post-processing omdb request.', exc_info=True)

            if omdbdata['Response'] == 'True':
                # make the keys all lower case
                omdbdata_lower = dict((k.lower(), v) for k, v in omdbdata.iteritems())
                data.update(omdbdata_lower)


        # get the snatched result score from SEARCHRESULTS
        gssr = self.sql.get_single_search_result(guid)
        if gssr:
            data['finishedscore'] = gssr['score']

        # remove any invalid characters
        for k, v in data.iteritems():
            # but we have to keep the path unmodified
            if k != 'path' and type(v) != int:
                data[k] = re.sub(r'[:"*?<>|]+', "", v)

        return data

    def renamer(self, data):
        '''
        Renames movie file based on renamerstring
        Returns new file name.
        '''
        renamer_string = self.pp_conf['renamerstring']

        existing_file_path = os.path.join(data['path'], data['filename'] + data['ext'])

        new_file_name =  renamer_string.format(**data)

        new_file_path = os.path.join(data['path'], new_file_name + data['ext'])

        logging.info('Renaming {} to {}'.format(existing_file_path, new_file_path))

        try:
            os.rename(existing_file_path, new_file_path)
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception, e:
            logging.error('Post-Processing Renamer.', exc_info=True)
            return False
        # return the new name so the mover knows what our file is
        return new_file_name


    def mover(self, data):
        '''
        Moves movie file to moverpath
        Returns True on success
        '''
        movie_file = os.path.join(data['path'], data['filename'] + data['ext'])

        mover_path = self.pp_conf['moverpath']

        target_folder = mover_path.format(**data)

        target_folder = os.path.normpath(target_folder)

        logging.info('Moving {} to {}'.format(movie_file, target_folder))

        try:
            if not os.path.exists(target_folder):
                os.mkdir(target_folder)
        except Exception, e:
            logging.error('Post-processing failed. Could not create folder.', exc_info=True)

        try:
            shutil.move(movie_file, target_folder)
        except Exception, e:
            logging.error('Post-processing failed. Could not move file.', exc_info=True)

        return True

    def cleanup(self, data):
        '''
        For a failed download, deletes data['path']
        '''
        remove_path = data['path']
        logging.info('Clean Up. Removing {}.'.format(remove_path))
        try:
            shutil.rmtree(remove_path)
        except Exception, e:
            logging.error('Post-processing failed. Could not clean up.', exc_info=True)
