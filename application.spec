# -*- mode: python -*-
a = Analysis(['application.py'],
             pathex=['/Users/XYK/Desktop/Dropbox/Choxue-scoreboard-OCR'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)

##### include mydir in distribution #######
def extra_datas(mydir):
    def rec_glob(p, files):
        import os
        import glob
        for d in glob.glob(p):
            if os.path.isfile(d):
                files.append(d)
            rec_glob("%s/*" % d, files)
    files = []
    rec_glob("%s/*" % mydir, files)
    extra_datas = []
    for f in files:
        extra_datas.append((f, f, 'DATA'))

    return extra_datas
###########################################

a.datas += extra_datas('static')
a.datas += extra_datas('ref_digits')
a.datas += [('athlete_data.csv','athlete_data.csv','DATA')]
a.datas += [('settings.ini','settings.ini','DATA')]
a.datas += [('index.html','index.html','DATA')]

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='application',
          debug=False,
          strip=None,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='application')