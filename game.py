# -*- coding: utf-8 -*-
from flask_socketio import SocketIO, join_room, emit

# json to parse json data
import json
# time is used to get the current time
import time
import datetime

# User Klasse anlegen
class User:
    def __init__(self):
        self.befehlsmarkerZeit = 0
        self.marschBefehleZeit = 0
        self.machtmarkerZeit = 0
        self.haus = ''
        self.name = ''
    def updateBefehle(self, time):
        if (self.befehlsmarkerZeit == 0):
            self.befehlsmarkerZeit = time
        else:
            self.befehlsmarkerZeit = (self.befehlsmarkerZeit + time) / 2
    def updateMarsch(self, time):
        if(self.marschBefehleZeit == 0):
            self.marschBefehleZeit = time
        else:
            self.marschBefehleZeit = (self.marschBefehleZeit + time) / 2
    def updateMachtmarker(self, time):
        if(self.machtmarkerZeit == 0):
            self.machtmarkerZeit = time
        else:
            self.machtmarkerZeit = (self.machtmarkerZeit + time) / 2
    def initialize(self,Haus, Name):
        self.haus = Haus
        self.name = Name


class Game: 
    # Spiel initialisieren
    def __init__(self,gamename, game_variant, numb_of_players):
        #Spielnamen initialisieren
        self.name = gamename
        # Spielkonfiguaration laden
        self.spiel = json.load(open('spiel_config.json'))
        # Spielstatistiken laden
        self.stats = json.load(open('stats.json'))
        self.spielerAnzahl = int(numb_of_players)
        # Liste mit spielbaren Häusern anlegen
        self.spielbareHauser = self.spiel['Spiel_Config']['spielbareHauser'][game_variant][numb_of_players]
        # neue Liste für die Reihenfolge anlegen (es werden immer Spieler aus der Liste geworfen die schon dran waren - nach der Runde wird sie wieder befüllt)
        self.reihenfolge = self.spielbareHauser.copy()
        # weitere Liste die angibt welche Spieler beim derzeitigen Spielzug noch nicht fertig sind
        self.nochNichtFertig = self.spielbareHauser.copy()
        # Variable für Rundenanzahl anlegen
        self.spielrunde = 1
        # ???
        self.AmZugReihenfolgeDurchgang = 0
        # Ein Dict das speichert wer wie viele Marschbefehle in der Runde gelegt hat
        self.gelegteMarschbefehle={}
        # ???
        self.hatAngegriffen = ''
        # Eine Varibale anlegen welche speichert wer gerade der Rabe ist
        self.rabe = ''
        # Eine Liste für alle Usernamen anlegen
        self.usernames = []
        # Ein Dict anleten welches Usernamen zu dem gewählten Haus mapped
        self.dictUserHaus = {}

        #Einige Variablen initialisieren um unterbrochene Spielverbindungen wieder zu aktualisieren
        # Derzeitigen Spielschritt als Variabel speichern
        self.Spielschritt =''
        # Variable für den Spieler der am Zug ist
        self.AmZug = ''
        # Festhalten wann der Timergestartet wurde
        self.timerStart = 0

        # Alle Spieler initialisieren und festlegen wer der Rabe ist
        self.rabenleistePositionen = []
        for haus in self.spielbareHauser:
            self.spiel['Spieler'][haus]['User'] = User()
            self.rabenleistePositionen.append(self.spiel['Spieler'][haus]['PositionenNormal']['konigshof'])
            self.gelegteMarschbefehle[haus] = 0
        self.rabenPosition = min(tuple(self.rabenleistePositionen))
        # Den Raben ermitteln (Rabe = Haus mit der niedrigsten Position auf der Königshofleiste)
        for self.haus in self.spielbareHauser:
            if(self.rabenPosition == self.spiel['Spieler'][self.haus]['PositionenNormal']['konigshof']):
                self.rabe = self.haus
        self.charToHouse = {
            'B': "Baratheon",
            'L':"Lannister",
            "S": "Stark",
            "M":"Martell",
            "G":"Greyjoy",
            "T":"Tyrell"
        }
        date = datetime.datetime.now()
        self.today = str(date.year) +'-'+str(date.month) +'-'+str(date.day)
    
    def sendMessage(self, ID, Nachricht, betroffener='Alle', schritt_erledigt=False, broadcast = True):
        nachricht = {
            'Name': self.name,
            'Betroffener': betroffener,
            'message': Nachricht
        }
        if schritt_erledigt:
            nachricht['erledigt'] = 'True'
        
        emit(ID, nachricht, broadcast = broadcast, room=self.name)
    
    def updateStatusAlle(self,status):
        for self.haus in self.spielbareHauser:
            self.spiel['Spieler'][self.haus]['Status'] = status

    def createTimer(self, aktion, zeit, betroffener):
        timer = {
            "Haus" : betroffener,
            "Aktion": aktion,
            "Zeit": zeit,
            'Geschehen':''
        }
        self.timerStart = time.time()
        if(betroffener != 'Alle'):
                timer["Geschehen"] = self.spiel['Spieler'][betroffener]['User'].name + ' ist am Zug!'
        return timer
    ####
    def verbleibendeZeit(self,zeit):
        now = time.time()
        result = int(self.timerStart - now) + zeit
        return result
    def alleBereit(self,Status):
        bereit = 0
        for haus in self.spielbareHauser:
            if(self.spiel['Spieler'][haus]['Status'] == Status):
                bereit += 1
        if(bereit == int(self.spielerAnzahl)):
            return True
        else:
            return False

    def neuenSpielerAktualisieren(self, haus):
        hausStatus = self.spiel['Spieler'][haus]['Status']
        print('Aktueller Status von {} == {}'.format(haus, hausStatus))

        if(self.Spielschritt == 'Joined'):
            if hausStatus == self.Spielschritt:
                self.sendMessage('joined','Alle', betroffener=haus, broadcast=False)
            else: # User hat diesen Schritt schon erledigt und wartet auf andere
                self.sendMessage('joined','Alle', betroffener=haus, schritt_erledigt=True, broadcast=False)
            self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig, betroffener=haus, broadcast=False)
        elif(self.Spielschritt == 'Start'):
            nachricht = {
                'msg': 'Spiel wird gestartet',
                'usernames':self.usernames
            }
            self.sendMessage('start', nachricht, betroffener=haus)
        elif(self.Spielschritt == 'Befehle'):
            timer = self.createTimer('Befehlsmarker legen', self.verbleibendeZeit(self.spiel['Spiel_Config']['Spielzugdauer']['BefehlsmarkerLegen']), haus)
            if hausStatus == self.Spielschritt:
                self.sendMessage('befehle', timer, betroffener=haus, broadcast=False)
            else: # User hat diesen Schritt schon erledigt und wartet auf andere
                self.sendMessage('befehle', timer, betroffener=haus, schritt_erledigt=True, broadcast=False)
            self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig, betroffener=haus, broadcast=False)
        elif(self.Spielschritt == 'Uberfall'):
            nachricht = {
                "rabe": self.rabe
            }
            if hausStatus == self.Spielschritt:
                self.sendMessage('uberfall',nachricht, betroffener=haus, broadcast=False)
            else: # User hat diesen Schritt schon erledigt und wartet auf andere
                self.sendMessage('uberfall',nachricht, betroffener=haus, schritt_erledigt=True, broadcast=False)
            self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig, betroffener=haus, broadcast=False)
        elif(self.Spielschritt == 'Marsch'):
            timer = self.createTimer('Marschbefehl ausführen', self.verbleibendeZeit(self.spiel['Spiel_Config']['Spielzugdauer']['Marschbefehl']), self.AmZug)
            self.sendMessage('marsch', timer, betroffener=haus, broadcast=False)
            self.nochNichtFertig = self.spielbareHauser.copy()
            try:
                self.nochNichtFertig.remove(self.AmZug)
            except:
                pass
            self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig, betroffener=haus, broadcast=False)
        elif(self.Spielschritt == 'Machtzuwachs'):
            timer = self.createTimer('Machtmarker nehmen', self.verbleibendeZeit(self.spiel['Spiel_Config']['Spielzugdauer']['Machtzuwachs']), haus)
            if hausStatus == self.Spielschritt:
                self.sendMessage('machtzuwachs', timer, betroffener=haus, broadcast=False)
            else: # User hat diesen Schritt schon erledigt und wartet auf andere
                self.sendMessage('machtzuwachs', timer, betroffener=haus, schritt_erledigt=True, broadcast=False)
            self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig, betroffener=haus, broadcast=False)
        elif(self.Spielschritt =='Westeros'):
            nachricht = {
                "nachricht": 'Westerosphase beginnt!'
            }
            self.sendMessage('westeros',nachricht, betroffener=haus, broadcast=False)
        print('---------------------')
        print('Spielschritt ' + self.Spielschritt + ' wiederhergestellt!')
        print('---------------------')

    def updateStats(self, haus, status, zeit):
        #daten = [status, zeit]
        self.user = self.spiel['Spieler'][haus]['User']
        if(status == 'Befehlsmarker gelegt'):
            self.user.updateBefehle(zeit)
        elif(status == 'Machtmarker genommen'):
            self.user.updateMachtmarker(zeit)
        elif(status == 'Marschbefehl ausgeführt'):
            self.user.updateMarsch(zeit)
        
    def createStat(self, haus):
        userObj = self.spiel['Spieler'][haus]['User']
        user = userObj.name
        daten = {
            "Befehlsmarker legen":userObj.befehlsmarkerZeit,
            "Marschausführen":userObj.marschBefehleZeit,
            "Machtmarker nehmen":userObj.machtmarkerZeit
        }
        if user in self.stats['Spieler'].keys(): # neue Statistik hinzufügen
            self.stats['Spieler'][user][self.today] = {}
            for spielzug in daten.keys():
                self.stats['Spieler'][user][self.today][spielzug] = daten[spielzug]
        else: #neuen User anlegen
            self.stats['Spieler'][user] = {self.today:{}}
            for spielzug in daten.keys():
                self.stats['Spieler'][user][self.today][spielzug] = daten[spielzug]
    #Funktionen die nacheinandern (verkehrte Reihenfolge) durchgeführt werden
    def westerosphaseEnde(self,data):
        if data['message']['change']:
            self.rabe = data['message']['rabe']
            self.reihenfolge = [ self.charToHouse[x] for x in data['message']['reihenfolge'].split() ]
        self.AmZugReihenfolgeDurchgang = 0
        self.spielrunde +=1
        self.startRound(self.spielrunde)

    def machtzuwachsMachen(self):
        print('---------------------')
        print('Machtzuwachsbefehle ausführen ...')
        timer = self.createTimer('Machtmarker nehmen', self.spiel['Spiel_Config']['Spielzugdauer']['Machtzuwachs'], 'Alle')
        self.updateStatusAlle('Machtzuwachs')
        self.sendMessage('machtzuwachs', timer)
        self.Spielschritt = 'Machtzuwachs'
        self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig)

    def angriffMachen(self, angreifer, verteidiger):
        now = time.time()
        zeit = int(now - self.timerStart)
        self.hatAngegriffen = angreifer
        self.updateStats(angreifer,'Marschbefehl ausgeführt', zeit)
        nachricht = {
            'Angreifer':angreifer,
            'Verteidiger':verteidiger
        }
        self.sendMessage('angriffMachen',nachricht)
    def marschMachen(self, haus):
        print('---------------------')
        print(haus + ' macht seinen Marsch')
        timer = self.createTimer('Marschbefehl ausführen', self.spiel['Spiel_Config']['Spielzugdauer']['Marschbefehl'], haus)
        self.sendMessage('marsch', timer)
        self.Spielschritt='Marsch'
        self.nochNichtFertig = self.spielbareHauser.copy()
        try:
            self.nochNichtFertig.remove(haus)
        except:
            pass
        self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig)
    
    def marschBefehle(self):
        maxIndex = self.spielerAnzahl -1
        print(self.gelegteMarschbefehle)
        self.kommendeMarschbefehle = 0
        for haus in self.reihenfolge:
            self.kommendeMarschbefehle += int(self.gelegteMarschbefehle[haus])
        if(self.kommendeMarschbefehle != 0): #Es gibt noch einen Marschbefehl
            self.AmZug = self.reihenfolge[self.AmZugReihenfolgeDurchgang]
            while (self.gelegteMarschbefehle[self.AmZug] == 0):
                print(self.AmZug +' hat keine Marschis mehr')
                if(self.AmZugReihenfolgeDurchgang < maxIndex):
                    self.AmZugReihenfolgeDurchgang += 1
                else:
                    self.AmZugReihenfolgeDurchgang = 0
                self.AmZug = self.reihenfolge[self.AmZugReihenfolgeDurchgang]
            if(self.gelegteMarschbefehle[self.AmZug] != 0):
                self.gelegteMarschbefehle[self.AmZug] -= 1
                if(self.AmZugReihenfolgeDurchgang < maxIndex):
                    self.AmZugReihenfolgeDurchgang += 1
                else:
                    self.AmZugReihenfolgeDurchgang = 0
                self.marschMachen(self.AmZug)
            else: #Es gibt keinen Marschbefehl mehr
                print('Fehler')
        else:  #Es gibt keinen Marschbefehl mehr
            self.machtzuwachsMachen()
        
    #Funktion für start der Runde >>> Die Funktion ruft die nächste auf undo weiter undso weiter

    def startRound(self,round):
        if(round <=10):
            print('--------------')
            print('--------------')
            print('Runde ' + str(round) + ' wird gestartet ...')
            
            # Führe ganze Runde aus
            #Reihenfolge aktualisieren
            # Befeghlsmarker legen
            self.updateStatusAlle('Befehle')
            print('---------------------')
            print('Befehlsmarker werden gelegt ...')
            timer = self.createTimer('Befehlsmarker legen', self.spiel['Spiel_Config']['Spielzugdauer']['BefehlsmarkerLegen'], 'Alle')
            self.sendMessage('befehle', timer)
            self.Spielschritt = 'Befehle'
            self.nochNichtFertig = self.spielbareHauser.copy()
            self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig)
        else:
            print('---------------------')
            print('Spiel ist zuende!')
            self.sendMessage('ende', 'Das Spiel ist zuende!')

    #Funktion mit der das Spiel gestartet wird >>> ruft startRunde() auf
    def startGame(self):
        self.usernames = []
        for haus in self.spielbareHauser:
            self.usernames.append(self.spiel['Spieler'][haus]['User'].name)
            self.dictUserHaus[self.spiel['Spieler'][haus]['User'].name] = haus
        nachricht = {
            'msg': 'Spiel wird gestartet',
            'usernames':self.usernames
        }
        self.sendMessage('start', nachricht)
        self.Spielschritt = 'Start'
        self.startRound(self.spielrunde)

    #Checkt ab ob alle Spieler bereit sind und wenn ja startet das Spiel mit startGame()
    def spielerBeitritt(self, Haus, User):
        self.spiel['Spieler'][Haus]['User'].initialize(Haus,User)
        self.spiel['Spieler'][Haus]['Status'] = 'Joined'
        try:
            self.nochNichtFertig.remove(Haus)
        except:
            pass
        self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig)
        if(self.alleBereit('Joined')):
            self.Spielschritt = 'Joined'
            self.sendMessage('joined','Alle')
            self.Spielschritt = 'Joined'
            self.nochNichtFertig = self.spielbareHauser.copy()
            self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig)
        else:
            self.sendMessage('joined', Haus, betroffener=Haus)

    def updateHausstatus(self, Haus,Status):
        now = time.time()
        self.zeit = int(now -self.timerStart)
        self.spiel['Spieler'][Haus]['Status'] = Status
        print('---------------------')
        print(Haus + ' >>> ' + self.spiel['Spieler'][Haus]['Status'])

        if(self.alleBereit(Status)):
            self.sendMessage('resetHausanzeige','')
            if(Status == 'bereitStart'):
                print('Starting the game ...')
                self.nochNichtFertig = self.spielbareHauser.copy()
                self.startGame()
            if(Status == 'Befehlsmarker gelegt'):
                self.updateStats(Haus,Status, self.zeit)
                self.nochNichtFertig = self.spielbareHauser.copy()
                self.Spielschritt = 'Uberfall'
                print('---------------------')
                print('Überfälle ausführen ...')
                self.updateStatusAlle('Uberfall')
                nachricht = {
                    "rabe": self.rabe
                }
                self.sendMessage('uberfall',nachricht)
                self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig)
            if(Status == 'uberfall gemacht'):
                self.updateStats(Haus,Status, self.zeit)
                self.nochNichtFertig = self.spielbareHauser.copy()
                print('---------------------')
                print('Marschbefehle ausführen ...')
                self.updateStatusAlle('Marsch')
                self.marschBefehle()
            if(Status == 'Machtmarker genommen'):
                self.updateStats(Haus,Status, self.zeit)
                self.nochNichtFertig = self.spielbareHauser.copy()
                self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig)
                nachricht = {
                    "betroffener": "Alle",
                    "nachricht": 'Westerosphase beginnt!'
                }
                self.sendMessage('westeros',nachricht)
                self.Spielschritt ='Westeros'
                print('---------------------')
                print('---------------------')
                print('Westerosphase beginnt ...')
                print('---------------------')
                print('---------------------')
                for haus in self.spielbareHauser:
                    self.createStat(haus)
                with open('stats.json', 'w') as outfile:
                    json.dump(self.stats, outfile, ensure_ascii=False,indent=4, sort_keys=True)  
            if(Status == 'westerosphaseFertig'):
                self.nochNichtFertig = self.spielbareHauser.copy()
                self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig)
        else:
            if(Status == 'Befehlsmarker gelegt'):
                self.updateStats(Haus,Status, self.zeit)
                try:
                    self.nochNichtFertig.remove(Haus)
                except:
                    pass
                self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig)
            if(Status == 'uberfall gemacht'):
                self.updateStats(Haus,Status, self.zeit)
                try:
                    self.nochNichtFertig.remove(Haus)
                except:
                    pass
                self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig)
            if(Status == 'Machtmarker genommen'):
                self.updateStats(Haus,Status, self.zeit)
                try:
                    self.nochNichtFertig.remove(Haus)
                except:
                    pass
                self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig)
            if(Status == 'bereitStart'):
                try:
                    self.nochNichtFertig.remove(Haus)
                except:
                    pass
                self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig)
            if(Status == 'westerosphaseFertig'):
                try:
                    self.nochNichtFertig.remove(Haus)
                except:
                    pass
                self.sendMessage('zeigeHausAnzeige', self.nochNichtFertig)
        if(Status == 'Marschbefehl ausgeführt'):
            if(self.hatAngegriffen == Haus):
                self.hatAngegriffen = ''
            else:
                self.updateStats(Haus,Status, self.zeit)
                self.hatAngegriffen = ''
            print('---------------------')
            print('Auf weitere Marschbefehle warten ...')
            self.marschBefehle()
    #Dieser Bereich definiert was mit den Nachrichten geschehen soll die an den Server gesendet werden        
    
    def initializeGame(self,data):
            message = {
                'User':data['Name'],
                'Hausliste':self.spielbareHauser
            }
            self.sendMessage('initialize',message)
    
    def on_join(self,data):
            self.spielerBeitritt(data['Haus'], data['Name'])
    
    def statusAktualisieren(self, data):
            stat = data['message']
            self.updateHausstatus(data['Haus'],stat)
    
    def angriff(self, data):
            print('++++++++++++++++++++++++')
            print(self.spiel['Spieler'][data['Angreifer']]['User'].name + ' greift ' + data['Verteidiger']+ ' an')
            print('++++++++++++++++++++++++')
            self.angriffMachen(data['Angreifer'], self.dictUserHaus[data['Verteidiger']])
    
    def restoreSession(self, data):
            print(str(data['Name']) + ' >>> restoring session ...')
            message = {
                'User':data['Name'],
                'Haus':'',
                'Hausliste':self.spielbareHauser,
                'Userliste' : self.usernames
            }
            
            if not data['Haus']:
                print(str(data['Name']) + ' noch nicht im Spiel >>> Neuen Spieler anlegen')
                self.sendMessage('initializeUser',message)
            else:
                user_restored = False
                for haus in self.spielbareHauser: # Loop through all houses
                    if(self.spiel['Spieler'][haus]['User'].name == data['Name']):
                        message['Haus'] = haus
                        emit('restoreHaus',message, broadcast = False, room=self.name)
                        user_restored = True
                if not user_restored:
                    emit('noGame', [], broadcast=False)              
    
    def restoreSchritt(self, data):
            print('Spielschritt wiederherstellen')
            self.neuenSpielerAktualisieren(data['Haus'])
    
    def anzahlBefehlsmarkerAktualisieren(self, data):
            haus = data['Haus']
            print(data['Anzahl'])
            anzahl = int(data['Anzahl'])
            self.gelegteMarschbefehle[haus] = anzahl
