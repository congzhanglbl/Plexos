import os
import codecs
import uuid
import xml.etree.cElementTree as etree
import time
import sqlite3 as sql
#import resource
import collections

class COAD(collections.MutableMapping):
  '''
      Edit models, horizons, memberships and object attributes of plexos data. Quickly modify the largest xml files for simulation.
      
      Instantiation will import xml data into a sqlite database or open an
      existing sqlite database of plexos data
      
      When import xml data, the new database will be saved as the same name as
      the file with a .db suffix instead of .xml
      
      When create_db_file is set to False, the new database will be created only
      in memory
    
      The class presents a map of class names to ClassDict objects
  '''
  store={}
  def __init__(self, filename = None, create_db_file=True):
    if filename is None:
      filename = os.path.abspath(os.path.dirname(__file__)) + os.sep + "master.xml"
    try:
      with open(filename):
        pass
    except:
      raise Exception('Unable to open %s'%filename)
    if filename.endswith('.db'):
        self.dbfilename=filename
        self.dbcon = sql.connect(self.dbfilename)
        self.populate_store()
    elif not filename.endswith('.xml'):
      raise Exception('Invalid filename suffix')
    else:
      self.load(filename,create_db_file)
    #self.populate_dict()

  def load(self,filename,create_db_file=True):
    ''' Load the xml file into a sqlite database
      Trust nothing, assume the worst on input by placing
      all table and column names in single quotes
      and feeding the text via parameterized SQL whenever possible
      At the end of load, populate the class dictionary
    '''
    start_time=time.time()
    if create_db_file:
      self.dbfilename = filename[:-4]+'.db'
    else:
      self.dbfilename =':memory:'
    print('Loading %s into %s'%(filename,self.dbfilename))
    tables={}
    nspace="{http://tempuri.org/MasterDataSet.xsd}"
    pk_exceptions = ['band'] # tables that don't adhere to PK standards
    nsl = len(nspace)
    t_check=nspace+'t_'
    row_count = 0
    self.dbcon = sql.connect(self.dbfilename)
    #with sql.connect(self.dbfilename) as con:
    #TODO: Check for existing database
    context=etree.iterparse(filename,events=('end',))#,tag="t_*")
    fk=[] # Foreign key list to add at the end of upload
    for action,elem in context:
      if t_check in elem.tag:
        table_name = elem.tag[nsl+2:]
        #print('Table '+table_name)
        col_names =[]
        col_values = []
        for el_data in elem.getchildren():
          col_names.append(el_data.tag[nsl:])
          col_values.append(el_data.text)
        # Check for new tables
        if table_name not in tables.keys():
          cols = []
          for col_name in col_names:
            if col_name.endswith('_id'):
              cols.append("'%s' INTEGER"%col_name)
              if col_name[:-3] == table_name and table_name not in pk_exceptions:
                cols[-1] += " PRIMARY KEY"
              else:
                fk.append((table_name,col_name))
                #print((table_name,col_name))
            else:
              cols.append("'%s' TEXT"%col_name)
          c_table = "CREATE TABLE '%s'(%s)"%(table_name,','.join(cols))
          #print(c_table)
          self.dbcon.execute("DROP TABLE IF EXISTS '%s';"%table_name)
          self.dbcon.execute(c_table)
          tables[table_name]=col_names
        # Check for new columns
        new_cols = set(col_names) - set(tables[table_name])
        # TODO make sure order isn't random on set diff
        for new_col in new_cols:
          m_table = "ALTER TABLE '%s' ADD COLUMN '%s' "%(table_name,new_col)
          if new_col.endswith('_id'):
            fk.append((table_name,new_col))
            #print((table_name,new_col))
            m_table += 'INTEGER'
          else:
            m_table += 'TEXT'
          #print(m_table)
          self.dbcon.execute(m_table)
          tables[table_name].append(new_col)
        i_row = 'INSERT INTO %s (%s) VALUES (%s)'%(table_name,','.join("'"+item+"'" for item in col_names),','.join('?'*len(col_values)))
        #print(i_row)
        try:
          self.dbcon.execute(i_row,col_values)
        except:
          print('Problem loading row %s with data %s'%(i_row,col_values))
          raise
        row_count+=1
    fk_tables = {}
    for (orig_table,orig_col) in fk:
      other_table = orig_col[:-3]
      if other_table in tables:
        if orig_table not in fk_tables:
          fk_tables[orig_table]=[]
        fk_tables[orig_table].append(orig_col)
        # This would be the best way to do this, but sqlite doesn't support
        # adding FKs after table creation
        #print ("ALTER TABLE %s ADD CONSTRAINT %s FOREIGN KEY ('%s') REFERENCES %s('%s')"%(orig_table,'fk_'+orig_col,orig_col,other_table,orig_col))
    # Have to move table, create new table with FKs, copy old data, delete old table
    for (table_name,fk_cols) in fk_tables.items():
      self.dbcon.executescript("DROP TABLE IF EXISTS %s_todelete;"%table_name)
      self.dbcon.execute("ALTER TABLE %s RENAME TO %s_todelete"%(table_name,table_name))
      col_cmds = []
      for col_name in tables[table_name]:
        if col_name.endswith('_id'):
          col_cmd = "'%s' INTEGER"%col_name
          if col_name[:-3] == table_name and table_name not in pk_exceptions:
            col_cmd += " PRIMARY KEY"
          col_cmds.append(col_cmd)
        else:
          col_cmds.append("'%s' TEXT"%col_name)
      # Foreign key defs must be after all column definitions
      for col_name in fk_cols:
        col_cmds.append("FOREIGN KEY ('%s') REFERENCES %s('%s')"%(col_name,col_name[:-3],col_name))
      self.dbcon.executescript("DROP TABLE IF EXISTS '%s';"%table_name)
      c_table = "CREATE TABLE '%s'(%s)"%(table_name,','.join(col_cmds))
      #print(c_table)
      self.dbcon.execute(c_table)
      self.dbcon.execute("INSERT INTO %s SELECT * FROM %s_todelete"%(table_name,table_name))
      self.dbcon.executescript("DROP TABLE IF EXISTS %s_todelete;"%table_name)
    self.tables=tables # Save table list for writing file
    self.populate_store()
    print('Loaded %s rows in %d seconds'%(row_count,(time.time()-start_time)))
  #  print('Memory usage: %s'%resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
  
  def populate_store(self):
    ''' Populate this map with class names and pointers to their classDict
      objects
    '''
    cur = self.dbcon.cursor()
    cur.execute("SELECT * FROM class")
    for row in cur.fetchall():
      c_meta=dict(zip([d[0] for d in cur.description],row))
      self.store[c_meta['name']]=ClassDict(self,c_meta)
    '''
      self[c['name']]=c
    # Cannot have multiple cursors - unreliable results
    for c in self.values():
      # Add objects that are this class to the dict
      # TODO: Collisions possible?  Do users ever need to look at class data?
      cur.execute("SELECT * FROM object WHERE class_id=?",[c['class_id']])
      for row in cur.fetchall():
        o=dict(zip([d[0] for d in cur.description],row))
        if o['name'] in c:
          raise Exception('Duplicate name of object %s in class %s'%(o['name'],c['name']))
        c[o['name']]=ObjectDict(self.dbcon,o)
    '''


  def save(self,filename):
    ''' Write current contents of database to xml
    '''
    # TODO: Check for overwrite existing
    #with sql.connect(self.dbfilename) as con:
    # Get list of objects with objname
    self.dbcon.row_factory=sql.Row
    cur = self.dbcon.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables=[t[0] for t in cur.fetchall()]
    #with open(filename,'w',encoding='utf-8') as f:
    with codecs.open(filename, "w", "utf-8-sig") as f:
      # file writing in Python3 is different than 2, have to convert
      # strings to bytes or open the file with an encoding.  There is no
      # easy write for all data types
      #f.write('\ufeff') # In order to match existing file
      #f.write(codecs.BOM_UTF8)
      f.write('<MasterDataSet xmlns="http://tempuri.org/MasterDataSet.xsd">\r\n')
      for table_name in sorted(tables):
      #for d_type in order:
      #  table_name = d_type[2:]
        try:
          cur.execute("SELECT * FROM '%s'"%(table_name))
        except:
          #print("Bad table %s"%table_name)
          continue
        row_keys = [k[0] for k in cur.description]
        #cElementTree has no pretty print, so some convolution is needed
        row = cur.fetchone()
        while row is not None:
          f.write('  ')
          ele = etree.Element('t_'+table_name)
          for (sube,val) in zip(row_keys,row):
            if val is None:
              continue
            attr_ele = etree.SubElement(ele,sube)
            if isinstance(val,int):
              val = str(val)
            attr_ele.text=val
          ele_slist = etree.tostringlist(ele)
          ''' This is done because in python2, to_string prepends the string with an
            xml declaration.  Also in python2, the base class of 'bytes' is basestring
            TODO: Will this ever process an element with no data?
            '''
          if isinstance(ele_slist[0],str):
            ele_s="".join(ele_slist)
          else:
            # Python3 bytes object
            ele_s=""
            for bl in ele_slist:
              ele_s+=bl.decode('UTF-8')
          f.write(ele_s.replace('><','>\r\n    <').replace('  </t_','</t_'))
          f.write('\r\n')
          row = cur.fetchone()
      f.write('</MasterDataSet>\r\n')


  def list(self,classname):
    ''' Print a list of all objects in class classname'''
    #with sql.connect(self.dbfilename) as con:
    cur = self.dbcon.cursor()
    cur.execute("SELECT name FROM object WHERE class_id IN (SELECT class_id FROM class WHERE name=?)",[classname])
    rows = cur.fetchall()
    for row in rows:
      print(row[0])

  def show(self,objname):
    ''' Print a list of all attributes in an object
      class_name.objname.attribute_name=attribute value
      
      attribute_data table has object_id, attribute_id, value
      attribute has attribute_name,
      object has object_id, class_id, object_name
      class has class_id,class_name
      
    '''
    #with sql.connect(self.dbfilename) as con:
    cur = self.dbcon.cursor()
    cur.execute("SELECT c.name as class_name,o.name as objname,a.name as attribute_name, ad.value as attribute_value FROM object o INNER JOIN class c ON c.class_id=o.class_id INNER JOIN attribute_data ad ON ad.object_id = o.object_id INNER JOIN attribute a ON a.attribute_id=ad.attribute_id WHERE o.name=?",[objname])
    attributes = cur.fetchall()
    for att in attributes:
      print('%s.%s.%s=%s'%tuple(att))

  def get(self,identifier):
    ''' Return the attribute value for an object
      class_name.object_name.attribute_name=attribute value
      
      attribute_data table has object_id, attribute_id, value
      attribute has attribute_name,
      object has object_id, class_id, object_name
      class has class_id,class_name
    '''
    try:
      (class_name,object_name,attribute_name)=identifier.split('.')
    except:
      raise Exception('''Invalid identifier, must take the form of:
        class name.object name.attribute name''')
    return self[class_name][object_name][attribute_name]

  def set(self,identifier,value):
    ''' Sets the attribute value for an object
      class_name.object_name.attribute_name=attribute value
      Will create a new row in attribute_data if no existing value is found
      '''
    try:
      (class_name,object_name,attribute_name)=identifier.split('.')
    except:
      raise Exception('''Invalid identifier, must take the form of:
        class name.object name.attribute name''')
    self[class_name][object_name][attribute_name]=value
          
  def diff(self,otherfilename):
    ''' Print a difference between two sqlite database files
        For each table in each db:
          Report differences in schema
          Report row differences
    '''
    def diff_table(table_name,cur1,cur2):
      ''' Print a difference between two tables
        First list schema differences
        Then data differences
        
        Assumes cursors have been created using sql.Row row_factory
      '''
      cur1.execute("SELECT * FROM '%s' ORDER BY 1,2"%(table_name))
      schema1 = [k[0] for k in cur1.description]
      data1 = cur1.fetchall()
      # Test the table on two - make sure all cols in one are still available
      cur2.execute("SELECT * FROM '%s' LIMIT 1"%(table_name))
      schema2 = [k[0] for k in cur2.description]
      if len(set(schema1) - set(schema2)) > 0:
        print("Table %s has different schemas"%table_name)
        return
      cur2.execute("SELECT %s FROM '%s' ORDER BY 1,2"%(','.join(["["+k+"]" for k in schema1]),table_name))
      data2 = cur2.fetchall()
      # At this point both data sets should be in the same order
      # For now use set functions to display differences
      in1 = set(data1)-set(data2)
      in2 = set(data2)-set(data1)
      if len(in1)>0 or len(in2)>0:
        print("Differences in table %s"%table_name)
        row_format = "{:>15}"*(len(schema1))
        if len(in1)>0:
          print("Only in original file:")
          print(row_format.format(*schema1))
          print('-'*15*len(schema1))
          for i in in1:
            print(row_format.format(*i))
        if len(in2)>0:
          print("Only in new file:")
          print(row_format.format(*schema1))
          print('-'*15*len(schema1))
          for i in in2:
            print(row_format.format(*i))
    if not otherfilename.endswith('.db'):
      raise Exception('Invalid filename extention for '+otherfilename)
    self.dbcon.row_factory=sql.Row
    cur = self.dbcon.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    tables = [s[0] for s in cur.fetchall()]
    with sql.connect(otherfilename) as other_con:
      other_con.row_factory=sql.Row
      other_cur = other_con.cursor()
      other_cur.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
      other_tables = [s[0] for s in other_cur.fetchall()]
      # Tables in both dbs
      for t in set(tables)|set(other_tables):
        diff_table(t,cur,other_cur)
      # Tables only in first db
      for t in set(tables)-set(other_tables):
        print('Tables removed from first file')
      # Tables only in second db
      for t in set(other_tables)-set(tables):
        print('Tables added to first file')

  def __setitem__(self,key,value):
    raise Exception('Operation not supported yet')

  def __getitem__(self,key):
    return self.store[key]
  
  def __delitem__(self,key):
    raise Exception('Operation not supported yet')
    #del self.store[key]
  
  def __iter__(self):
    return iter(self.store)
  
  def __len__(self):
    return len(self.store)




class ClassDict(collections.MutableMapping):
  '''     
    meta is a dictionary describing the class to match the
    database entry
    
    Uses Abstract Base Classes to extend a dictionary
    '''
  def __init__(self,coad,meta):
    self.store = dict()
    self.coad = coad
    self.meta = meta
    cur = self.coad.dbcon.cursor()
    cur.execute("SELECT * FROM object WHERE class_id=?",[self.meta['class_id']])
    for row in cur.fetchall():
      o=dict(zip([d[0] for d in cur.description],row))
      if o['name'] in self.store:
        raise Exception('Duplicate name of object %s in class %s'%(o['name'],self.meta['name']))
      self.store[o['name']]=ObjectDict(self.coad,o)
  
  def __setitem__(self,key,value):
    ''' Allow setting keys to an objectdict '''
    if not isinstance(value,ObjectDict):
      raise Exception('Unable to set Class child to anything but Object')
    # TODO: Some kind of validation in databaseland
    self.store[key]=value
  
  def __getitem__(self,key):
    return self.store[key]
  
  def __delitem__(self,key):
    # To remove this object:
    #   Remove all attribute data associated with the object
    #   Remove all records from membership where this is the parent_id
    #   TODO: Should objects not associated with any other object that
    #         were children of this object be deleted as well?
    #   Remove record from object
    raise Exception('Opertation not supported yet')
    # TODO: remove attribute data from db
    #del self.store[key]
  
  def __iter__(self):
    return iter(self.store)
  
  def __len__(self):
    return len(self.store)

class ObjectDict(collections.MutableMapping):
  ''' Overwrites the setitem method to allow updates to data and dict
    Works by using the list of attribute and attribute data dicts
    and manipulating the original database as needed
    
    meta is a dictionary describing the object as it is described in the
    database
    
    Uses Abstract Base Classes to extend a dictionary
    '''
  def __init__(self,coad,meta):
    self.store = dict()
    self.coad = coad
    self.meta = meta
    cur = self.coad.dbcon.cursor()
    self._no_update = True
    # Populate current values
    cur.execute("SELECT a.name as attribute_name, ad.value as attribute_value FROM attribute_data ad INNER JOIN attribute a ON a.attribute_id=ad.attribute_id WHERE ad.object_id=?",[self.meta['object_id']])
    for a in cur.fetchall():
      self[a[0]]=a[1]
    # Populate allowed values
    self.valid_attributes = {}
    cur.execute("SELECT a.* FROM attribute a INNER JOIN object o ON o.class_id=c.class_id INNER JOIN class c ON o.class_id=a.class_id WHERE o.object_id=?",[self.meta['object_id']])
    for row in cur.fetchall():
      a=dict(zip([d[0] for d in cur.description],row))
      self.valid_attributes[a['name']]=a
    self._no_update=False
  
  def __setitem__(self,key,value):
    if self._no_update:
      self.store[key]=value
      #super(ObjectDict, self).__setitem__(key,value)
      return
    # TODO: Make sure value is valid
    existing_att_data = False
    # Make sure this attribute is allowed in this class
    if key not in self.valid_attributes:
      raise Exception('%s is not a valid attribute of object %s, valid attributes:%s'%(key,self.meta['name'],self.valid_attributes.keys()))
    cur = self.coad.dbcon.cursor()
    cur.execute("UPDATE attribute_data SET value=? WHERE object_id=? and attribute_id=?",[value,self.meta['object_id'],self.valid_attributes[key]['attribute_id']])
    if cur.rowcount == 0:
      # Did not work, add a new row
      cur.execute("INSERT INTO attribute_data (object_id,attribute_id,value) VALUES (?,?,?)",[self.meta['object_id'],self.valid_attributes[key]['attribute_id'],value])
    self.coad.dbcon.commit()
    # Can replace the above statements with the following once a unique
    # identifier is placed in attribute_data
    # Should be on (object_id,attribute_id)
    #cur.execute("INSERT OR REPLACE INTO attribute_data (object_id,attribute_id,value) VALUES (?,?,?) WHERE object_id=? and attribute_id=?",[self.meta['object_id'],self.valid_attributes[key]['attribute_id'],value,self.meta['object_id'],self.valid_attributes[key]['attribute_id']])
    #super(ObjectDict, self).__setitem__(key,value)
    self.store[key]=value

  def __getitem__(self,key):
      return self.store[key]
      
  def __delitem__(self,key):
    cur = self.coad.dbcon.cursor()
    cur.execute("DELETE FROM attribute_data WHERE object_id=? AND attribute_id=?",[self.meta['object_id'],self.valid_attributes[key]['attribute_id']])
    self.coad.dbcon.commit()
    del self.store[key]
  
  def __iter__(self):
    return iter(self.store)
  
  def __len__(self):
    return len(self.store)

  def __str__(self):
    return repr(self.store)
  
  def copy(self, newname=None):
    ''' Create a new object entry in the database, duplicate all the 
      attribute_data entries as well.
      # TODO: Enforce unique naming
    '''
    cols = []
    vals = []
    for (k,v) in self.meta.items():
      if k != 'object_id':
        cols.append(k)
        if k == 'name':
          if newname is None:
            v=self.meta['name']+'-'+str(uuid.uuid4())
          else:
            v=newname
        vals.append(v)
    cur = self.coad.dbcon.cursor()
    fill = ','.join('?'*len(cols))
    #print("INSERT INTO object (%s) VALUES (%s)"%(','.join(["'%s'"%c for c in cols]),fill))
    cur.execute("INSERT INTO object (%s) VALUES (%s)"%(','.join(["'%s'"%c for c in cols]),fill),vals)
    self.coad.dbcon.commit()
    new_obj_meta=dict(zip(cols,vals))
    new_obj_meta['object_id']=cur.lastrowid
    new_obj_dict = ObjectDict(self.coad,new_obj_meta)
    for (k,v) in self.store.items():
      new_obj_dict[k]=v
    # Add this objectdict to classdict
    new_obj_dict.get_class()[new_obj_meta['name']]=new_obj_dict
    #for class_name, class_dict in self.coad.items():
    #  if class_dict.meta['class_id'] == new_obj_meta['class_id']:
    #    class_dict[new_obj_meta['name']]=new_obj_dict
    #    break
    #print('last id is %s'%cur.lastrowid)
    #print(cur.fetchall())
    # Create new the membership information
    # TODO: Is it possible to have orphans by not checking child_object_id?
    cur.execute("SELECT * FROM membership WHERE parent_object_id=?",[self.meta['object_id']])
    cols =[d[0] for d in cur.description]
    parent_object_id_idx=cols.index('parent_object_id')
    for row in cur.fetchall():
      newrow=list(row)
      newrow[parent_object_id_idx]=new_obj_meta['object_id']
      #cur.execute("INSERT INTO membership (%s) VALUES (?)",[newrow])
      #cur.execute("INSERT INTO membership (%s) VALUES (%s)"%(','.join(["'"+d[0]+"'" for d in cur.description[1:]]),','.join(['?' for d in newrow[1:]])),[newrow[1:]])
      cur.execute("INSERT INTO membership (%s) VALUES (%s)"%(','.join(["'"+c+"'" for c in cols[1:]]),','.join(['?' for d in newrow[1:]])),newrow[1:])
      #print("INSERT INTO membership (%s) VALUES (%s)"%(','.join(["'"+d[0]+"'" for d in cur.description[1:]]),repr(newrow[1:])))
    self.coad.dbcon.commit()
    return new_obj_dict

  def set_children(self,children,replace=True):
    ''' Set the children of this object.  If replace is true, it will remove any existing children
        matching the classes passed in otherwise it will append the data
        Can handle either a single ObjectDict or list of ObjectDicts
        TODO: Validate that object is allowed to have the children passed in
    '''
    children_by_class={}
    if isinstance(children,ObjectDict):
      class_id=children.get_class().meta['class_id']
      children_by_class[class_id]=[children]
    else:
      for od in children:
        if not isinstance(od,ObjectDict):
          raise Exception("Children must be of type ObjectDict, passed item was %s"%(type(od)))
        class_id=od.get_class().meta['class_id']
        if class_id not in children_by_class.keys():
          children_by_class[class_id]=[od]
        else:
          children_by_class[class_id].append(od)
    cur = self.coad.dbcon.cursor()
    for (class_id,objectdicts) in children_by_class.items():
      if replace:
        cur.execute("DELETE FROM membership WHERE parent_object_id=? AND child_class_id=?",[self.meta['object_id'],class_id])
      collection_id=self.get_collection_id(class_id)
      for od in objectdicts:
        cur.execute("INSERT INTO membership (parent_class_id,parent_object_id,collection_id,child_class_id,child_object_id) VALUES (?,?,?,?,?)",[self.meta['class_id'],self.meta['object_id'],collection_id,class_id,od.meta['object_id']])
    self.coad.dbcon.commit()



    # Sort into dict where class_id is the key and a list of object_dicts is the value
    # Validate every member of children is an ObjectDict
    # For each class
    #   If replace is True remove existing membership entries for the class
    #   Add all objects to membership
    # commit
    
  
  
  def get_children(self,class_name=None):
    ''' Return a list of all children that match the class name
    '''
    children=[]
    cur = self.coad.dbcon.cursor()
    select="SELECT c.name AS class_name,o.name AS object_name FROM membership INNER JOIN class c ON c.class_id=child_class_id INNER JOIN object o ON o.object_id=child_object_id WHERE parent_object_id=?"
    s_params=[self.meta['object_id']]
    if class_name is not None:
      select = select+" and c.name=?"
      s_params.append(class_name)
    cur.execute(select,s_params)
    for row in cur.fetchall():
      children.append(self.coad[row[0]][row[1]])
    return children

  def get_class(self):
    ''' Return the ClassDict that contains this object
    '''
    for class_name, class_dict in self.coad.items():
      if class_dict.meta['class_id'] == self.meta['class_id']:
        return class_dict
    raise Exception('Unable to find class associated with object')

  def get_collection_id(self,child_class_id):
    ''' Return the collection id that represents the relationship between this object's class and a
      child's class
      Collections appear to be another view of membership, maybe a list of allowed memberships
    '''
    cur = self.coad.dbcon.cursor()
    cur.execute("SELECT collection_id FROM collection WHERE parent_class_id=? and child_class_id=?",[self.meta['class_id'],child_class_id])
    rows=cur.fetchall()
    if len(rows) != 1:
      raise Exception('Unable to find collection for the parent %s and child %s'%(self.meta['class_id'],child_class_id))
    return rows[0][0]
  
  def dump(self, recursion_level=0):
    ''' Print to stdout as much information as possible about object to facilitate debugging
    '''
    spacing = '    '*recursion_level
    print(spacing+'Object:  {:<30}      ID: {:d}'.format(self.meta['name'],self.meta['object_id']))
    print(spacing+'  Class: {:<30}      ID: {:d}'.format(self.get_class().meta['name'],self.meta['class_id']))
    if self.keys():
      print(spacing+'  Attributes set:')
      for a in self.items():
        print(spacing+'    %s = %s'%a)
    else:
      print(spacing+'  No attributes set')
    kids = self.get_children()
    if len(kids):
      print(spacing+'  Children (%s):'%len(kids))
      for k in kids:
        k.dump(recursion_level+1)
    else:
      print(spacing+'  No children')

  def print_object_attrs(self):
    ''' Prints the object's attributes in Class.Object.Attribute=Value format
    '''
    c_name = self.get_class().meta['name']
    for (k,v) in self.items():
      print('%s.%s.%s=%s'%(c_name,self.meta['name'],k,v))



  '''
  def update(self,*args,**kwargs):
    if args:
      if len(args) > 1:
        raise TypeError("update expected at most 1 arguments, got %d" %len(args))
      other = dict(args[0])
      for key in other:
        self[key] = kwargs[key]
    for key in kwargs:
      self[key] = kwargs[key]
  
  def setdefault(self, key, value=None):
    if key not in self:
      self[key]=value
    return self[key]
  '''
