import getelnum
import numpy as np
import matplotlib.pyplot as plt
import readstars
import postfit
import matchstars
from scipy.optimize import leastsq
import starsdb
import sqlite3
import scipy
import scipy.stats as stats
import pdb
import flt2tex

class Plotgen():

    ###Pull up database.
    conn = sqlite3.connect('stars.sqlite')
    cur = conn.cursor()    
    feherr = 0.03
    tefferr= 44

    elements = ['O','C']

    for elstr in elements:
        cmd = 'SELECT %s_abund,%s_staterrlo,%s_staterrhi FROM mystars '\
            % (elstr,elstr,elstr)
        wcmd = ' WHERE '+postfit.globcut(elstr)
        cur.execute(cmd+wcmd)

        temptype =[('abund',float),('staterrlo',float),('staterrhi',float)]
        arr = np.array(cur.fetchall(),dtype=temptype)
        arr = [np.abs(np.median(arr['staterrlo'])),np.median(arr['staterrhi'])]
        #stats is lo, hi
        exec(elstr+'stats = arr')    
    
    def tfit(self,save=False,fitres=False):
        """
        A quick look at the fits to the temperature
            """
        line = [6300,6587]
        subplot = ((1,2))
        f = plt.figure( figsize=(6,6) )
        f.set_facecolor('white')  #we wamt the canvas to be white

        f.subplots_adjust(hspace=0.0001)
        ax1 = plt.subplot(211)
        ax1.set_xticklabels('',visible=False)
        ax1.set_yticks(np.arange(-0.8,0.4,0.2))

        ax2 = plt.subplot(212,sharex=ax1)
        ax1.set_ylabel('[O/H]')
        ax2.set_ylabel('[C/H]')
        ax2.set_xlabel('$\mathbf{ T_{eff} }$')
        ax = (ax1,ax2)

        for i in range(2):
            o = getelnum.Getelnum(line[i])           
            elstr = o.elstr.upper()

            fitabund, fitpar, t,abund = postfit.tfit(line[i])    
            if fitres:
                abund = fitabund

            tarr = np.linspace(t.min(),t.max(),100)        
            ax[i].scatter(t,abund,color='black',s=10)
            ax[i].scatter(o.teff_sol,0.,color='red',s=30)
            ax[i].plot(tarr,np.polyval(fitpar,tarr),lw=2,color='red')        

            exec('yerr = self.'+elstr+'stats')
            yerr = [[yerr[0]],[yerr[1]]]
            inv = ax[i].transData.inverted()
            errpt = inv.transform( ax[i].transAxes.transform( (0.9,0.9) ) )
            print errpt
            ax[i].errorbar(errpt[0],errpt[1],xerr=self.tefferr,
                           yerr=yerr,capsize=0)


        if save:
            plt.savefig('Thesis/pyplots/teff.ps')


    def feh(self,save=False,noratio=False):
        """
        Show the trends of X/Fe as a function of Fe/H.
        """
        #pull in fitted abundances from tfit

        lines = [6300,6587]
        flags  = ['dn','dk']

        binmin = -0.5
        binwid = 0.1
        nbins = 11
        qtype= [('abund',float),('feh',float),('staterrlo',float),
                ('staterrhi',float),('pop_flag','|S10')]    
        
        bins = np.linspace(binmin,binmin+binwid*nbins,nbins)

        subplot = ((1,2))
        f = plt.figure( figsize=(6,6) )
        f.set_facecolor('white')  #we wamt the canvas to be white

        f.subplots_adjust(hspace=0.0001)
        ax1 = plt.subplot(211)
        ax1.set_xticklabels('',visible=False)
        ax2 = plt.subplot(212,sharex=ax1)



        ax2.set_xlabel('[Fe/H]')
        ax = (ax1,ax2)


        for i in range(2):
            p = getelnum.Getelnum(lines[i])           
            elstr = p.elstr

            cmd = 'SELECT %s_abund,fe_abund,%s_staterrlo,%s_staterrhi,pop_flag FROM mystars ' % (elstr,elstr,elstr)
            wcmd = ' WHERE '+postfit.globcut(elstr)+' AND pop_flag = "dn"'

            self.cur.execute(cmd+wcmd)
            arrthin = np.array(self.cur.fetchall(),dtype=qtype)
            
            arrthin['abund'] -= p.abnd_sol

            wcmd = ' WHERE '+postfit.globcut(elstr)+' AND pop_flag = "dk"'
            self.cur.execute(cmd+wcmd)

            arrthick = np.array(self.cur.fetchall(),
                           dtype=qtype)
            arrthick['abund'] -= p.abnd_sol

                                
            if noratio:
                ythin = arrthin['abund']
                ythick = arrthick['abund']
                ax[i].set_ylabel('[%s/H]' % (elstr) )
            else:
                ythin = arrthin['abund'] -arrthin['feh']
                ythick = arrthick['abund'] -arrthick['feh']
                ax[i].set_ylabel('[%s/Fe]' % (elstr) )

            ### Compute Avg Thin disk in bins ###
            binind = np.digitize(arrthin['feh'],bins)
            binx,biny = [] , []
            for j in np.arange(nbins-1)+1:
                ind = (np.where(binind == j))[0]
                binx.append(binmin+binwid*(j-0.5))
                biny.append(np.mean(ythin[ind]))
                
            binx,biny = np.array(binx),np.array(biny)            


            ax[i].plot(arrthin['feh'],ythin,'bo')
            ax[i].plot(arrthick['feh'],ythick,'go')
            ax[i].plot(binx,biny,'rx-',lw=2,ms=5,mew=2)

            #plot typical errorbars

            leg = ax[i].legend( ('Thin Disk','Thick Disk','Binned Thin Disk'), loc='best')
            for t in leg.get_texts():
                t.set_fontsize('small')


            exec('yerr = self.'+elstr+'stats')
            yerr = [[yerr[0]],[yerr[1]]]
            inv = ax[i].transData.inverted()
            errpt = inv.transform( ax[i].transAxes.transform( (0.9,0.9) ) )
            ax[i].errorbar(errpt[0],errpt[1],xerr=self.feherr,
                           yerr=yerr,capsize=0)

        yticks = ax2.get_yticks()[:-1]
        ax2.set_yticks(yticks)


        if save:
            plt.savefig('Thesis/pyplots/feh.ps')


    def abundhist(self,save=False):
        """
        Plot the distributions of abundances.  Possibly not needed with the exo 
        plot.
        """
        #pull in fitted abundances from tfit

        line = [6300,6587]
        antxt = ['[O/H]','[C/H]']

        subplot = ((1,2))
        f = plt.figure( figsize=(6,6) )

        f.subplots_adjust(hspace=0.0001)
        ax1 = plt.subplot(211)
        ax1.set_xticklabels('',visible=False)
        ax1.set_yticks(np.arange(0,200,50))

        ax2 = plt.subplot(212,sharex=ax1)
        ax2.set_yticks(np.arange(0,200,50))
        ax2.set_xlabel('[Fe/H]')
        ax = (ax1,ax2)

        outex = []
        for i in range(2):
            p = getelnum.Getelnum(line[i])           
            fitabund,x,x,x = postfit.tfit(line[i])
            ax[i].set_ylabel('Number of Stars')
            ax[i].hist(fitabund,range=(-1,1),bins=20,fc='gray')
            ax[i].set_ylim(0,200)
            ax[i].annotate(antxt[i],(-0.8,150))
            N,m,s,min,max = fitabund.size,fitabund.mean(), \
                fitabund.std(),fitabund.min(),fitabund.max()
            if save:
            #output moments for tex write up
                outex.append(r'$\text {%s}$& %i & %.2f & %.2f & %.2f & %.2f\\'
                             % (antxt[i],N,m,s,min,max))
            else:
                print 'N, mean, std, min, max' + antxt[i]
                print '(%i,%f,%f,%f,%f)' % (N,m,s,min,max)
                
        if save:
            plt.savefig('Thesis/pyplots/abundhist.ps')
            f = open('Thesis/tables/abundhist.tex','w')
            f.writelines(outex)

    def comp(self,save=False,texcmd=False):
    ###
    ###  Bensby corrects his 6300 abundances for a non-LTE effect which shifts the
    ###  correlation away from mine by about 0.1 dex
    ###
        tables = [['ben05'],['luckstars']]
        offset = [[0],[8.5]]
        literr = [[0.06],[0.1]]

        lines = [6300,6587]
        color = ['blue','red','green']


        f = plt.figure( figsize=(6,8) )
        ax1 = plt.subplot(211)
        ax2 = plt.subplot(212)
        ax1.set_xlabel('[O/H], Bensby 2005')
        ax2.set_xlabel('[C/H], Luck 2006')

        ax1.set_ylabel('[O/H], This Work')
        ax2.set_ylabel('[C/H], This Work')
        ax = [ax1,ax2]
        ncomp = []

        for i in [0,1]:        
            xtot =[] #total array of comparison studies
            ytot =[] #total array of comparison studies

            p = getelnum.Getelnum(lines[i])
            elstr = p.elstr
            abnd_sol = p.abnd_sol

            print abnd_sol
            for j in range(len(tables[i])):
                table = tables[i][j]            

                #SELECT
                cmd = """
SELECT DISTINCT 
mystars.%s_abund,mystars.%s_staterrlo,
mystars.%s_staterrhi,%s.%s_abund""" % (elstr,elstr,elstr,table,elstr)
                if table is 'luckstars':
                    cmd = cmd + ','+table+'.c_staterr '

                #FROM WHERE
                cmd = cmd + ' FROM mystars,%s WHERE mystars.oid = %s.oid AND %s.%s_abund IS NOT NULL AND %s' % (table,table,table,elstr,postfit.globcut(elstr))
                if table is 'luckstars':
                    cmd = cmd+' AND '+table+'.c_staterr < 0.3'

                self.cur.execute(cmd)
                arr = np.array(self.cur.fetchall())
                x = arr[:,3] - offset[i][j]
                y = arr[:,0] -abnd_sol

                ###pull literature errors###
                if table is 'ben05':
                    xerr = np.zeros( (2,len(x)) ) + 0.06
                if table is 'luckstars':
                    xerr = arr[:,4].tolist()
                    xerr = np.array([xerr,xerr])            

                yerr = np.abs(arr[:,1:3])
                print cmd
                n = len(x)
                ncomp.append(n)
                print str(n) + 'comparisons'

                ax[i].errorbar(x,y,xerr=xerr,yerr=yerr.transpose(),color=color[j],
                               marker='o',ls='None',capsize=0,markersize=5)
                xtot.append( x.tolist() )
                ytot.append( y.tolist() )            

            line = np.linspace(-3,3,10)

            xtot=np.array(xtot)        
            ytot=np.array(ytot)
            symerr = (yerr[:,0]+yerr[:,1])/2.

            ax[i].plot(line,line)
            ax[i].set_xlim((-0.6,+0.6))
            ax[i].set_ylim((-0.6,+0.6))

            print np.std(xtot[0]-ytot[0])
        plt.draw()
        if texcmd:
            return ncomp

        if save:
            plt.savefig('Thesis/pyplots/comp.ps')


    def exo(self,save=False):
        """
        Show a histogram of Carbon and Oxygen for planet harboring stars, and
        comparison stars.
        """
        f = plt.figure( figsize=(6,8) )
        f.subplots_adjust(top=0.95,bottom=0.05)

        elements = ['O','C','Fe']
        nel = len(elements)
        sol_abnd = [8.7,8.5,0]

        ax = []  #empty list to store axes
        outex = []
        for i in range(nel): #loop over the different elements
            ax.append(plt.subplot(nel,1,i+1))
            elstr = elements[i]
            ax[i].set_xlabel('['+elstr+'/H]')

            if elstr is 'Fe':
                cmd0 = 'SELECT distinct(mystars.oid),mystars.'+elstr+'_abund '+\
                    ' FROM mystars LEFT JOIN exo ON exo.oid = mystars.oid WHERE '
            else:
                cmd0 = 'SELECT distinct(mystars.oid),mystars.'+elstr+'_abund '+\
                    ' FROM mystars LEFT JOIN exo ON exo.oid = mystars.oid '+\
                    ' WHERE '+postfit.globcut(elstr)+' AND '

            #Grab Planet Sample
            cmd = cmd0 +' exo.name IS NOT NULL'
            self.cur.execute(cmd)
            #pull arrays and subtract solar offset
            arrhost = np.array( self.cur.fetchall() ,dtype=float)[:,1] - sol_abnd[i]    
            nhost = len(arrhost)

            #Grab Comparison Sample
            cmd = cmd0 +' exo.name IS NULL'
            self.cur.execute(cmd)
            #pull arrays and subtract solar offset
            arrcomp = np.array( self.cur.fetchall() ,dtype=float)[:,1] - sol_abnd[i] 
            ncomp = len(arrcomp)

            # Make histogram
            ax[i].hist([arrcomp,arrhost], 20, normed=1, histtype='bar',
                       label=['Comparison','Planet Hosts'])
            ax[i].legend(loc='upper left')

            ######## Compute KS - statistic or probablity #########
            mhost,shost,mcomp,scomp = np.mean(arrhost),np.std(arrhost),\
                np.mean(arrcomp),np.std(arrcomp)

            D,p = stats.ks_2samp(arrhost,arrcomp)

            if save:
                # element number mean std ncomp compmean compstd KS p
                outex.append(r'%s & %i & %.2f & %.2f & & %i & %.2f & %.2f & %.2f & %s \\' % (elstr,nhost,mhost,shost,ncomp,mcomp,scomp,D,flt2tex.flt2tex(p,sigfig=1) ) )

            else:
                print elstr+' in stars w/  planets: N = %i Mean = %f Std %f ' \
                    % (nhost,mhost,shost)
                print elstr+' in stars w/o planets: N = %i Mean = %f Std %f ' \
                    % (ncomp,mhost,shost)
                print 'KS Test: D = %f  p = %f ' % (D,p)

        plt.draw()
        if save:
            plt.savefig('Thesis/pyplots/exo.ps')
            f = open('Thesis/tables/exo.tex','w')
            f.writelines(outex)


    def cofe(self,save=False):
        cmd0 = 'SELECT distinct(mystars.oid),'+\
            ' mystars.o_abund,mystars.c_abund,mystars.fe_abund '+\
            ' FROM mystars LEFT JOIN exo ON exo.oid = mystars.oid '+\
            ' WHERE '+postfit.globcut('C')+' AND '+postfit.globcut('O')

        qtype= [('oid','|S10'),('o_abund',float),('c_abund',float),('feh',float)]

        #Grab Planet Sample
        cmd = cmd0 +' AND exo.name IS NOT NULL'
        self.cur.execute(cmd)
        #pull arrays and subtract solar offset
        arrhost = np.array( self.cur.fetchall() ,dtype=qtype)
        nhost = len(arrhost)

        #Grab Comparison Sample
        cmd = cmd0 +' AND exo.name IS NULL'
        self.cur.execute(cmd)
        #pull arrays and subtract solar offset
        arrcomp = np.array( self.cur.fetchall() ,dtype=qtype)
        ncomp = len(arrcomp)

        #calculate C/O  logeps(c) - logeps(o)
        c2ohost = 10**(arrhost['c_abund']-arrhost['o_abund'])
        c2ocomp = 10**(arrcomp['c_abund']-arrcomp['o_abund'])

        f = plt.figure( figsize=(6,4) )
        ax = plt.subplot(111)
        ax.plot(arrcomp['feh'],c2ocomp,'bo')
        ax.plot(arrhost['feh'],c2ohost,'go')
        ax.legend(('Comparision','Hosts'))
        ax.set_xlabel('[Fe/H]')
        ax.set_ylabel('C/O')

        yerr = [[np.sqrt( np.log(10)*( self.Cstats[0]**2+self.Ostats[0]**2 ))],
                [np.sqrt( np.log(10)*( self.Cstats[1]**2+self.Ostats[1]**2 ))]]
        inv = ax.transData.inverted()
        errpt = inv.transform( ax.transAxes.transform( (0.8,0.8) ) )
        ax.errorbar(errpt[0],errpt[1],xerr=self.feherr,
                       yerr=yerr,capsize=0)

        ax.set_ybound(0,ax.get_ylim()[1])
        ax.axhline(1.)
        plt.show()
        if save:
            plt.savefig('Thesis/pyplots/cofe.ps')
        return ax
        
    def compmany(self,elstr='o'):
        if elstr == 'o':
            tables = ['mystars','luckstars','ramstars']
        if elstr =='c':
            tables = ['mystars','luckstars','red06']

        ncomp = len(tables)
        for i in range(ncomp):
            for j in range(ncomp):
                if i != j:
                    tabx = tables[i]
                    taby = tables[j]

                    colx = tabx+'.'+elstr+'_abund'
                    coly = taby+'.'+elstr+'_abund'
                    cut  = ' WHERE '+tabx+'.oid = '+taby+'.oid '+'AND '+\
                        colx+' IS NOT NULL AND '+coly+' IS NOT NULL '
                    if tabx == 'mystars' or taby == 'mystars':
                        cut = cut+' AND '+postfit.globcut(elstr) 

                    ax = plt.subplot(ncomp,ncomp,i*ncomp+j+1)
                    cmd = 'SELECT DISTINCT '+colx+','+coly+' FROM '+tabx+','+taby+cut
                    self.cur.execute(cmd)

                    arr = np.array(self.cur.fetchall())
                    if len(arr) > 0:
                        (x,y) = arr[:,0],arr[:,1]
                        ax.scatter(x-x.mean(),y-y.mean())

                    ax.set_xlabel(tabx)
                    ax.set_ylabel(taby)
                    xlim = ax.get_xlim()
                    x = np.linspace(xlim[0],xlim[1],10)
                    ax.plot(x,x,color='red')

        plt.draw()
        self.conn.close()




