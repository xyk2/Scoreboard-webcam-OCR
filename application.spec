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
a.datas += [('ssocr','ssocr','DATA')]
a.datas += [('settings.ini','settings.ini','DATA')]
a.datas += [('_away_score.jpg','_away_score.jpg','DATA')]
a.datas += [('_game_clock.jpg','_game_clock.jpg','DATA')]
a.datas += [('_GC_ssocr_processed.jpg','_GC_ssocr_processed.jpg','DATA')]
a.datas += [('_SC_ssocr_processed.jpg','_SC_ssocr_processed.jpg','DATA')]
a.datas += [('_home_score.jpg','_home_score.jpg','DATA')]
a.datas += [('_shot_clock.jpg','_shot_clock.jpg','DATA')]
a.datas += [('_ssocr_processed.jpg','ssocr_processed.jpg','DATA')]
a.datas += [('clock_1.jpg','clock_1.jpg','DATA')]
a.datas += [('clock_2.jpg','clock_2.jpg','DATA')]
a.datas += [('clock_3.jpg','clock_3.jpg','DATA')]
a.datas += [('clock_4.jpg','clock_4.jpg','DATA')]
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