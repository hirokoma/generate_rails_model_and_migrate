# -*- coding: utf-8 -*-
import re
import subprocess
from datetime import datetime
from fabric.colors import green
from fabric.colors import red
import inflect
import copy

p = inflect.engine()

app_name = 'MYAPP'

def exec_command(cmd):
    return subprocess.Popen(
        cmd, stdout=subprocess.PIPE,
        shell=True).stdout.readlines()

models = []
new_model = {
  'name': '',
  'relations': [],
  'validations': [],
  'migrations': [],
  'index': []
}

csv_file_path = './model.csv'
lines = []

with open(csv_file_path, 'r') as f:
    lines = f.readlines()

for line in lines[3:]:
    line = line.strip()
    line = re.sub(r'\"(.+?),(.+?)\"', r'\1@\2', line)
    cols = line.split(',')
    cols = map(lambda x: x.replace('@', ','), cols)

    # Model
    if cols[0] != '':
        models.append(copy.deepcopy(new_model))
        models[-1]['name'] = cols[0]
    
    if cols[1] == '' and cols[7] == '':
        continue

    # Relation
    if cols[1] != '-':
        relation = ','.join([
            '{} :{}'.format(cols[1], cols[2]),
            'polymorphic: {}'.format(cols[3]) if cols[3] != '-' else '',
            'as: :{}'.format(cols[4]) if cols[4] != '-' else '',
            'class_name: \'{}\''.format(cols[5]) if cols[5] != '-' else '',
            'foreign_key: :{}'.format(cols[6]) if cols[6] != '-' else '',
        ])

        relation = re.sub(r',+', ', ', relation)
        relation = re.sub(r',\s\Z', '', relation)

        models[-1]['relations'].append(relation)

    # Validation, Migration
    if cols[7] != '-':
        validation = ',\n'.join([
            'validates :{}'.format(cols[7]),
            '  presence: {}'.format(cols[13]) if cols[13] != '-' else '',
            '  absence: {}'.format(cols[14]) if cols[14] != '-' else '',
            '  exclusion: {{ in: {} }}'.format(cols[15]) if cols[15] != '-' else '',
            '  inclusion: {{ in: {} }}'.format(cols[16]) if cols[16] != '-' else '',
            '  format: {{ with: {} }}'.format(cols[17]) if cols[17] != '-' else '',
            '  length: {' if ''.join(cols[18:22]) != '----' else '',
            '    minimum: {}'.format(cols[18]) if cols[18] != '-' else '',
            '    maximum: {}'.format(cols[19]) if cols[19] != '-' else '',
            '    in: {}'.format(cols[20]) if cols[20] != '-' else '',
            '    is: {}'.format(cols[21]) if cols[21] != '-' else '',
            '  }' if ''.join(cols[18:22]) != '----' else '',
            '  numericality: {' if ''.join(cols[22:30]) != '--------' else '' ,
            '    only_integer: {}'.format(cols[22]) if cols[22] != '-' else '',
            '    greater_than: {}'.format(cols[23]) if cols[23] != '-' else '',
            '    less_than: {}'.format(cols[24]) if cols[24] != '-' else '',
            '    greater_than_or_equal_to: {}'.format(cols[25]) if cols[25] != '-' else '',
            '    less_than_or_equal_to: {}'.format(cols[26]) if cols[26] != '-' else '',
            '    equal_to: {}'.format(cols[27]) if cols[27] != '-' else '',
            '    odd: {}'.format(cols[28]) if cols[28] != '-' else '',
            '    even: {}'.format(cols[29]) if cols[29] != '-' else '',
            '  }' if ''.join(cols[22:30]) != '--------' else '',
            '  uniqueness: {}'.format(cols[30]) if cols[30] != '-' else '',
            '  uniqueness: {' if ''.join(cols[31:33]) != '--' else '',
            '    scope: {}'.format(cols[31]) if cols[31] != '-' else '',
            '    case_sensitive: {}'.format(cols[32]) if cols[32] != '-' else '',
            '  }' if ''.join(cols[31:33]) != '--' else '',
            '  acceptance: {}'.format(cols[33]) if cols[33] != '-' else '',
            '  allow_nil: {}'.format(cols[34]) if cols[34] != '-' else '',
            '  allow_blank: {}'.format(cols[35]) if cols[35] != '-' else '',
        ])

        validation = re.sub(r'\{,', '{', validation)
        validation = re.sub(r'^,\n', '', validation, flags=re.MULTILINE)
        validation = re.sub(r',\n\Z', '', validation, flags=re.MULTILINE)
        validation = re.sub(r',\n(\s*\})', r'\n\1', validation)

        models[-1]['validations'].append(validation)
        
        
        migration = ','.join([
            'add_column :{},:{},:{}'.format(
                p.plural(models[-1]['name'].lower()),
                cols[7],
                cols[8]
            ) if models[-1]['name'] == 'User' else '',
            't.{} :{}'.format(cols[8], cols[7]) if models[-1]['name'] != 'User' else '',
            'default: {}'.format(cols[9].replace('[ ]', '\'\'')) if cols[9] != '-' else '',
            'null: {}'.format(cols[10]) if cols[10] != '-' else '',
            'precision: {}'.format(cols[11]) if cols[11] != '-' else '',
            'scale: {}'.format(cols[12]) if cols[12] != '-' else ''
        ])
        migration = re.sub(r',,+', ',', migration)
        migration = re.sub(r',\Z', '', migration)
        migration = re.sub(r',', ', ', migration)
        migration = re.sub(r'\A,', '', migration)

        models[-1]['migrations'].append(migration)



for i, model in enumerate(models):
    # Model file
    file_path = './{}/app/models/{}.rb'.format(app_name, model['name'].lower())

    result = exec_command('([ -e {} ] && echo 1 ) || echo 0'.format(file_path))
    file_exists = bool(int(result[0].strip()))
    if not file_exists:
        body = '\n'.join([
          '\n'.join(model['relations']),
          '',
          '\n\n'.join(model['validations'])
        ])
        body = re.sub(r'^', '  ', body, flags=re.MULTILINE)
        body = '\n'.join([
          'class {} < ApplicationRecord\n'.format(model['name']),
          body,
          'end'
        ])
        f = open(file_path, 'w')
        f.write(body)
        f.close()
        print green('Success: {} created'.format(file_path))
    else:
        print red('Failed: {} already exists.'.format(file_path))

    # Migrate file
    file_path = './{}/db/migrate/{}_{}_{}.rb'.format(
        app_name,
        datetime.now().strftime('%Y%m%d%H%M') + str(i).zfill(2),
        'add_columns_to' if model['name'] == 'User' else 'create',
        p.plural(model['name'].lower())
    )

    result = exec_command('([ -e {} ] && echo 1 ) || echo 0'.format(file_path))
    file_exists = bool(int(result[0].strip()))
    if not file_exists:
        body = '\n'.join(model['migrations'])
        body = re.sub(r'^', '      ', body, flags=re.MULTILINE)
        body = '\n'.join([
          'class {}{} < ActiveRecord::Migration[5.0]\n'.format(
              'AddColumnsTo' if model['name'] == 'User' else 'Create',
              p.plural(model['name'])
          ),
          '  def change',
          '    create_table :{} do |t|'.format(p.plural(model['name'].lower())) if model['name'] != 'User' else '',
          body,
          '    end' if model['name'] != 'User' else '',
          '  end',
          'end'
        ])
        f = open(file_path, 'w')
        f.write(body)
        f.close()
        print green('Success: {} created'.format(file_path))
    else:
        print red('Failed: {} already exists.'.format(file_path))

