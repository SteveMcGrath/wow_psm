#!/usr/bin/env python

import cmd
import os
import sys
import re
import time
import MySQLdb
import getpass
from commands import getoutput as run

version = '0.0.1a'
motd = '''
WoW Private Server Manager Version %s
----------------------------------------------
Written By: Steven McGrath

     Notes: Verifications?  We don't need no stinkin' verifications!
            Also, Tony needs to look at this code :-p
            Extra formatting for your pleasure :D
''' % version

class Database(object):
  databases = {}
  def __init__(self, config='/opt/arcemu/server/etc'):
    for configfile in ['world.conf', 'logon.conf']:
      db_directives = re.findall(r'<\w+Database[^>]*>', 
                                 open('%s/%s' % (config, configfile)).read())
      for directive in db_directives:
        conf = {}
        for line in directive.split('\n\t'):
          dset = line.split('=')
          if len(dset) > 1:
            conf[dset[0].lower().strip()] = dset[1].strip().strip('>').strip('"')
          else:
            if dset[0].find('Database') > -1:
              name  = re.findall(r'<(\w+)Database',dset[0])[0].lower()
        self.databases[name] = MySQLdb.connect(host=conf['hostname'],
                                               user=conf['username'],
                                               passwd=conf['password'],
                                               db=conf['name'],
                                               port=int(conf['port']))
  
  def add_user(self, username, password, level):
    cursor  = self.databases['logon'].cursor()
    cursor.execute('''
      INSERT INTO accounts (login, password, gm, flags, banned)
      VALUES ('%s','%s','%s',24,0)
    ''' % (username, password, level))
    cursor.close()
  
  def set_ban(self, username, reason):
    cursor  = self.databases['logon'].cursor()
    cursor.execute('''
      UPDATE accounts
         SET banned = '1', banreason = '%s'
       WHERE login = '%s'
    ''' % (reason, username))
    cursor.close()
  
  def unset_ban(self, username):
    cursor  = self.databases['logon'].cursor()
    cursor.execute('''
      UPDATE accounts
         SET banned = 0, banreason = NULL
       WHERE login = '%s'
    ''' % username)
    cursor.close()
  
  def del_user(self, username):
    cursor  = self.databases['logon'].cursor()
    cursor.execute('''
      DELETE FROM accounts
       WHERE login = '%s'
    ''' % username)
    cursor.close()
  
  def get_user(self, username):
    cursor  = self.databases['logon'].cursor()
    cursor.execute('''
      SELECT *
        FROM accounts
       WHERE login = '%s'
    ''' % username)
    row = cursor.fetchone()
    cursor.close()
    return row
  
  def get_list(self):
    cursor  = self.databases['logon'].cursor()
    cursor.execute('''
      SELECT *
        FROM accounts
    ''')
    rows = cursor.fetchall()
    cursor.close()
    return rows
  
  def update_user(self, username, field, value):
    cursor  = self.databases['logon'].cursor()
    cursor.execute('''
      UPDATE accounts
         SET %s = '%s'
       WHERE login = '%s'
    ''' % (field, value, username))
    cursor.close()
    
    
class WOWManagerCLI(cmd.Cmd):
  intro     = motd
  prompt    = 'WoW Manager> '
  db        = Database()
  location  = '/opt/arcemu/server'
  
  def do_exit(self, s):
    '''
    exit
    
    guess.
    '''
    sys.exit(0)
  
  def do_add(self, s):
    '''
    add [username] [gm level]
    Creates a new account on the server.
    '''
    dset  = s.split()
    if len(dset) == 2:
      user    = dset[0]
      level   = dset[1]
      passwd  = getpass.getpass()
      self.db.add_user(user,passwd,level)
      # Need to Add verification here
    else:
      throw_error()
  
  def do_ban(self, s):
    '''
    ban [username] [reason]
    Bans the user from the server
    '''
    if len(s.split()) > 1:
      user    = s.split()[0]
      reason  = ' '.join(s.split()[1:])
      self.db.set_ban(user, reason)
    else:
      throw_error()
  
  def do_unban(self, s):
    '''
    unban [username]
    Un-bans the user from the server
    '''
    if len(s) > 1:
      self.db.unset_ban(s)
    else:
      throw_error()
  
  def do_del(self, s):
    '''
    del [username]
    Deletes a user fromt he database
    '''
    if len(s) > 1:
      self.db.del_user(s)
    else:
      throw_error()
  
  def do_get(self, s):
    '''
    get [username]
    Gets the specified user's information
    '''
    if len(s) > 1:
      print_acct(self.db.get_user(s))
    else:
      throw_error()
  
  def do_list(self, s):
    '''
    list
    Lists all users.
    '''
    for row in self.db.get_list():
      print_acct(row)
  
  def do_update(self, s):
    '''
    update [username] [field] [value]
    '''
    if len(s.split()) > 2:
      user  = s.split()[0]
      field = s.split()[1]
      value = s.split()[2]
      self.db.update_user(user, field, value)
    else:
      throw_error()
  
  def do_password(self, s):
    '''
    password [username]
    '''
    if len(s) > 1:
      passwd  = getpass.getpass()
      self.db.update_user(s,'password',passwd)
    else:
      throw_error()
    
  
  def do_service(self, s):
    '''
    service [start|stop|restart] [logon|world]
    '''
    if len(s) > 3:
      svcs  = {
        'logon': 'arcemu-logonserver',
        'world': 'arcemu-world',
      }
      dset = s.split()
      action  = dset[0].lower()
      if len(dset) > 1:
        services = [dset[1],]
      else:
        services = ['logon','world']
    
      if action in ['stop','restart']:
        for service in services:
          pid = get_pid(svcs[service])
          if pid is not None:
            os.kill(pid, 15)
            while get_pid(svcs[service]) is not None:
              print 'Waiting for %s to stop...' % service
              time.sleep(1)
      if action in ['start', 'restart']:
        for service in services:
          print 'Starting %s service...' % service
          os.system('screen -dmS %s bash -c \'cd %s/bin;./%s\'' %\
                    (service, self.location, svcs[service]))
    else:
      throw_error()
            
          
        
def get_pid(name):
  try:
    pid = int(run('ps -C %s -o pid=' % name))
  except:
    pid = None
  return pid

def print_acct(row):
  try:
    last_log = row[6].ctime()
  except AttributeError:
    last_log = 'NEVER'
  print '[%2s] %-30s %15s %s' % (row[4],row[1],row[7],last_log)
  if row[5] > 0:
    print '  ** BANNED: %s' % row[12]

def throw_error():
  print 'You dun typed somthin\' wrong...'

if __name__ == '__main__':
  if len(sys.argv) > 1:
      WOWManagerCLI().onecmd(' '.join(sys.argv[1:]))
  else:
      WOWManagerCLI().cmdloop()  