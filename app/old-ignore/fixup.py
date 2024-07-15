import os

'''
This code was used to remove files in softwareUse that
were duplicated.
'''



path = 'dynamicSearch/softwareUse'
copy = 'copy'

def fix():
    files = os.listdir(path)
    for file in files:
        if copy in file:
            file = path + '/' + file
            print(file)
            os.remove(file)

fix()