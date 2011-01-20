#!/usr/bin/python

import os, re, sys, getopt
import audioconvert, statusbar

audio_f = {'m4a': [], 'wma': []}
bad_files, good_files = [], []
good_outfile, bad_outfile = None, None 
delete_flag = 0

def usage(message):
    sys.stderr.write ('vquac.py: %s\n' % message) 
    sys.stderr.write ('''\
Usage: vquac.py [OPTION]... DIR 

Convert all files in DIR with .m4a and .wma suffix to mp3,
while attempting to maintain quality, and meta data. 

  -d Delete successfully converted original .m4a and .wma files
  -g FILE   Print names of all 'Good'/successfully converted 
            .m4a and .wma files to FILE
  -b FILE   Print names of all 'Bad'/failed converted 
            .m4a and .wma files to FILE
  -h (help) display this message

''')
    sys.exit (1)

try:
    opts, args = getopt.getopt (sys.argv[1:], 'hb:g:d')
    for option, value in opts:
        if option == '-d':
            delete_flag = 1
        elif option =='-h':
            usage('help message')
        else:
            try:
                if option == '-g':
                    good_outfile = open(value, 'w')
                elif option =='-b':
                    bad_outfile = open(value, 'w')
            except:
                raise VError, 'Could not open file %d', option
except (getopt.error), e:
    usage(e)
        
if len(args) != 1:
    usage('No \'DIR\' provided.')   

if delete_flag == 1:
    print 'Sure you want to delete all original m4a and wma files? [y/n]'
    response = raw_input(">")
    if response != 'y':
        usage('')


print 'Finding all .m4a and .wma files in ' + args[0] 
print 'Please be patient, this may take a few seconds...'

out = os.walk(args[0])
for dir, dirnames, files in out:
    for f in files:
        # files that don't start w/ '.' and end w/ .m4a or .wma
        match = re.search('^[^.].+[.](wma|m4a)$', f, re.IGNORECASE)
        if match:
            type = match.group(1).lower() 
            audio_f[ type ].append(dir + '/' + f)

print str(len( audio_f['m4a'] )) + '\tm4a files found.' 
print str(len( audio_f['wma'] )) + '\twma files found.' 


print '\nConverting m4a files...'
m4a_bar = statusbar.StatusBar(0, len(audio_f['m4a']) ) 
m4a_bar.start()
for mp4_f in audio_f['m4a']:
    if audioconvert.m4a_to_mp3(mp4_f):
        bad_files.append( mp4_f )
    else:
        good_files.append( mp4_f )
        if delete_flag == 1:
            os.remove(mp4_f)
    m4a_bar.increment() 
m4a_bar.join()

print '\nConverting wma files...'
wma_bar = statusbar.StatusBar(0, len(audio_f['wma']) ) 
wma_bar.start()
# loop and start converting wma files
for wma_f in audio_f['wma']:
    if audioconvert.wma_to_mp3(wma_f):
        bad_files.append( wma_f )
    else:
        good_files.append( wma_f ) 
        if delete_flag == 1:
            os.remove(wma_f)
    wma_bar.increment()
wma_bar.join()
print '\n\n\n'

print str(len(good_files)) + ' files sucessfully converted.'
print str(len(bad_files))  + ' files could not be converted.'
for f in bad_files:
    print f

if good_outfile:
    for f in good_files:
        good_outfile.write(f +'\n')
    good_outfile.close()
if bad_outfile:
    for f in bad_files:
        bad_outfile.write(f +'\n')
    bad_outfile.close()
