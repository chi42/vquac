import os
import re
import tempfile
import subprocess

from mutagen.mp3 import MP3
from mutagen.asf import ASF 
from mutagen.mp4 import MP4
from mutagen.easyid3 import EasyID3

# list of allowed bitrates (in kb) for lame encoder
lame_bits = [96, 112, 128, 144, 192, 224, 256, 320]
#Comment = ''#FIXME

# need file pointer to /dev/null and writeable for later uses
dev_null = open('/dev/null', 'w')

# takes original file bitrate, 
# return mp3 LAME VBR quality and bitrate (in kb) in a list
# LAME bitrate is slightly more then original bitrate
# VBAR quality is normally 4, and 0 (higher) if o_bit is very high
def bit_v_set(o_bit):
    # o_bit is usually in bytes, not kb, but try to check
    if o_bit >= 1000:
        o_bit /= 1000 

    if o_bit >= lame_bits[ len(lame_bits) - 1]:
        bitrate = lame_bits[ len(lame_bits) - 1 ]
        vbr = 2 
    else:
        bitrate, vbr = 0, 4 
        for bitrate in lame_bits:
            if o_bit < bitrate:
                break
    return [bitrate, vbr]

# converts wav file to mp3 using 'lame'
# inputs:
#   audio_meta  - hash table of pertinent meta data, where keys are
#       elements in meta tags for mp3 file 
#   tmp_file    - temporary file containing raw PCM audio
#   org_name    - orginal name (full path name is allowed) of file
#   bitrate     - bitrate to set the new mp3 file to 
# return:
#   0 on success, nonzero otherwise 
def wav_to_mp3(audio_meta, tmp_file, org_name, bitrate):
    b_and_v = bit_v_set(bitrate) 
    # get filename of orginal file (minus path suffix), strip out wma/m4a
    new_file = os.path.dirname(org_name) + \
              '/' +\
              re.search('([^/]+)(\.wma|\.m4a)', 
              org_name, re.IGNORECASE).group(1) +\
              '.mp3'

    # call lame to perform the conversion
    returncode = subprocess.Popen(['lame', 
        '--quiet', '--nohist', '--vbr-new',
        '-b', str(b_and_v[0]),
        '-V' + str(b_and_v[1]), 
        '-q2',
        '--add-id3v2',
        tmp_file, 
        new_file,
            ]
        ).wait()
    
    # set meta data
    mp3_audio = EasyID3(new_file)
    for key, val in audio_meta.items():
        #print key, val
        mp3_audio[key] = val

    # push changes to new mp3 file 
    mp3_audio.save()
    return returncode

# extracts meta data from a wma info, and presents it in a form
#   understandable to mp3   
# input:
#   w_audio - wma file's metadata in dictionary
# return:
#   dictionary of metadata, where keys are in a form to be made
#       understandable by the mp3 conversion process
def get_wma_info(w_audio):
    wma_info = {} 
    #if w_audio['Author']:
    if 'Author' in w_audio:
        wma_info['artist'] = w_audio['Author']
    elif 'WM/AlbumArtist' in w_audio:
        wma_info['artist'] = w_audio['WM/AlbumArtist']
    else:
        wma_info['artist'] = 'Unknown Artist'
    # album
    if 'WM/AlbumTitle' in w_audio:
        wma_info['album'] = w_audio['WM/AlbumTitle']
    else:
        wma_info['album'] = 'Unknown Album'
    # year of song 
    if 'WM/Year' in w_audio:
        wma_info['date'] = str( w_audio['WM/Year'] )
    else:
        wma_info['date'] = ''
    # track number
    if 'WM/TrackNumber' in w_audio:
        wma_info['tracknumber'] = str(w_audio['WM/TrackNumber'][0])
    else:
        wma_info['tracknumber'] = '' 
    # song title
    if 'Title' in w_audio:
        wma_info['title'] = w_audio['Title']
    else:
        wma_info['title'] = 'Unknown Track' 
    # genre
    if 'WM/Genre' in w_audio:
        wma_info['genre'] = w_audio['WM/Genre']
    else:
        wma_info['genre'] = '' 

    return wma_info

# extracts meta data from a m4a info, and presents it in a form
#   understandable to mp3   
# input:
#   a_audio - m4a file's metadata in dictionary
# return:
#   dictionary of metadata, where keys are in a form to be made
#       understandable by the mp3 conversion process
def get_m4a_info(a_audio):
    a_info = {}
    # album
    if '\xa9alb' in a_audio: 
        a_info['album'] = a_audio['\xa9alb']
    else:
        a_info['album'] = 'Unknown Album'
    # year of song 
    if '\xa9day' in a_audio: 
        a_info['date'] = a_audio['\xa9day']
    else:
        a_info['date'] = ''
    # artist
    if '\xa9ART' in a_audio:
        a_info['artist'] = a_audio['\xa9ART']
        # composer
    elif '\xa9wrt'in a_audio:
        a_info['artist'] = a_audio['\xa9wrt']
    else:
        a_info['artist'] = 'Unknown Artist'
    # song title
    if '\xa9nam' in a_audio:
        a_info['title'] = a_audio['\xa9nam']
    else:
        a_info['title'] = 'Unknown Track'
    # genre
    if '\xa9gen' in a_audio:
        a_info['genre'] =  a_audio['\xa9gen']
    else:
        a_info['genre'] = ''
    # track number and track total
    #a_info['tracknumber'] = a_audio['trkn']
    if 'trkn' in a_audio:
        if len(a_audio['trkn']) == 1:
            if len(a_audio['trkn'][0]) >= 1:
                a_info['tracknumber'] = str(a_audio['trkn'][0][0])  
            if len(a_audio['trkn'][0]) == 2:
                a_info['tracknumber'] += '/'
                a_info['tracknumber'] += str(a_audio['trkn'][0][1])
    else:
        a_info['tracknumber'] = ''

    return a_info

# return 0 if file is good 
# return 1 if file is bad 
def wma_to_mp3(wma_f):
    returncode = 0
    try:
        # try to catch bad files
        audio = ASF( wma_f )     
    except:
        returncode = 1
        #bad_files.append( wma_f )
        #continue
    # determine bitrate and qualtiy settings for new mp3
    if returncode == 0:
        t_file = tempfile.NamedTemporaryFile()
        returncode = subprocess.Popen(
            ['mplayer', wma_f ,'-ao', 'pcm:file=' + t_file.name],
            stdout=dev_null, stderr=dev_null ).wait()
        if returncode == 0:
            returncode = wav_to_mp3( get_wma_info(audio), 
                t_file.name, wma_f, audio.info.bitrate ) 
        t_file.close()

    return 0

def m4a_to_mp3( mp4_f ):
    returncode = 0
    try:
        audio = MP4( mp4_f )
    except:
        returncode = 1
        #bad_files.append( mp4_f )
        #continue
    #good_files.append( mp4_f )
    if returncode == 0:
        t_file = tempfile.NamedTemporaryFile()

        returncode = subprocess.Popen(
            ['faad', mp4_f, '-o', t_file.name], 
            stdout=dev_null, stderr=dev_null ).wait()
        if returncode == 0:
            returncode = wav_to_mp3( get_m4a_info(audio), 
                t_file.name, mp4_f, audio.info.bitrate ) 
        t_file.close()

    return 0

