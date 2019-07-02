binding
	
	#������������ ����
	precseries	= prec_dec.tss;	# mm/day	#������ �� 10 �����
	meanTempseries	= taver_dec.tss;		#������� �������������� ����������� ������� �� 10 �����
	maxTempseries	= tmax_dec.tss;		#������������ �������������� ����������� ������� �� 10 �����
	minTempseries	= tmin_dec.tss;		#����������� �������������� ����������� �� ����������� ����� �� 10 �����
	stationpoly	= friction.map;		#����� ������������ ��������� ������������
	stationpoints	= station.map;		#����� ������������
	
	#��������� ������
	dem		= latest_dtm.map;			#�������� ������ �������
	riverldd	= ldd_catchment.ldd;		#���������-�������� ���� ����������
	whold		= whold_cover.map;		#����� ������� ������������ �����
	cropfactor	= cropf_cover.map;		#����� ������������� ������������ ��������� �� ��������� ���������������	
	observationpoint	=q_obs.map;			#���������� �����
	thorni	= thorn_i.lut;			#������� ��������� I � ������� ���������� ��� ������ ������������
	thorna	= thorn_a.lut;			#������� ��������� � � ������� ���������� ��� ������ ������������
	nrdaystss	=nrdays10.tss;
	daylenghtss	=daylen10.tss;
	snowfalltriggertemp	=0.7;			#����������� ������ ���������
	snowmeltrate	=30;	#mm/deg*tstep	#������������� �����������
	daypertimestep	=10;				#���������� ���� �� 1 ���
	snowmelttemp	=4;				#����������� ������ �����������
	soilfreezetemp	=-1;				#����������� ������ ����������� �����
	soilthawtemp	=2;				#����������� ������ ����������
	separationconst	=0.6;				#����������� ������������                                                             	recession	=0.01;				#����������� ��������� �����
					
	
	
timer 
1	36	1;
initial
#��������� ������� 	
	soilstorage	=0;	#���������� � ����� (��)
	snowcover 	=0;	#������ �������� ������� (��)
	soilfrozen 	=0;	#��������� ����� (1 - ���������, 0 - �����������)
	basereservoir	=200;	#������� ��������� �����
	upstreamarea	=accuflux(riverldd,1); #������� ��������� �� ����������� ������
	dp=1.2;	#��������� ���������� �������
	dt=2;		#��������� �����������
dynamic
	#	������������� ������� �� ���������� ������� �������� ���������
	precipitationpoints=timeinputscalar(precseries,stationpoints)*daypertimestep;	#mm/tstep
	precipitation=inversedistance(defined(dem),precipitationpoints,2,0,0);

	#	������������� ����������� �� ���������� ������� �������� ���������
	meanTemppoints=timeinputscalar(meanTempseries,stationpoints);
	meanTemp=inversedistance(defined(dem),meanTemppoints,2,0,0);
	minTemppoints=timeinputscalar(minTempseries,stationpoints);
	minTemp=inversedistance(defined(dem),minTemppoints,2,0,0);
	maxTemppoints=timeinputscalar(maxTempseries,stationpoints);
	maxTemp=inversedistance(defined(dem),maxTemppoints,2,0,0);
	
	#	��������� ������ � ������� �������, ����������� � ������ �������� �������
	snowfall=if(meanTemp lt snowfalltriggertemp then precipitation else 0);	#mm/tstep
	snowcover=snowfall+snowcover;		#mm
	snowmelt=min(snowcover, if(meanTemp gt snowmelttemp then snowmeltrate*meanTemp else 0));	#mm/tstep
	snowcover=snowcover-snowmelt;
	rainfall=precipitation-snowfall;	#mm/tstep
	
	#	����������� �����
	soilfreeze=minTemp lt soilfreezetemp;
	soilthaw=(snowcover eq 0) and (meanTemp gt soilthawtemp);
	soilfrozen=(soilfrozen or soilfreeze) and not (soilthaw);
	
	#	������������ �� ����������
	heatindex=lookupscalar(thorni,stationpoly);
	aindex=lookupscalar(thorna,stationpoly);
	tmp=cover((10*meanTemp/heatindex)**aindex,0);
	potevap=if((meanTemp gt 0) and (heatindex ge 0) then 16*tmp*timeinputscalar(daylenghtss,stationpoly) else 0);
	potevapcorr=0.1*(timeinputscalar(nrdaystss,1)/30);
	pottotal=potevap*cropfactor;
	evaporation=min(pottotal,soilstorage);	
	soilstorage=soilstorage-evaporation;	

	#	������������� ���� � ������������
	surfacewater=rainfall+snowmelt;	#mm/tstep	
	filtration=if(soilfrozen then 0 else min(surfacewater,100));	#mm/tstep
	runoff=surfacewater-filtration;		#mm/tstep
	soilstorage=soilstorage+filtration;
	excess=max(0,soilstorage-whold);	#mm/tstep
	soilstorage=soilstorage-excess;
	percolation=excess*separationconst;	#mm/tstep

	
	#	�������� ����
	basereservoir=basereservoir+percolation;	#mm
	baseflow=basereservoir*recession;	#mm/tstep
	basereservoir=basereservoir-baseflow;	#mm

	#	��������� ����
	quickflow=runoff+excess-percolation;	#mm/tstep
	discharge=quickflow+baseflow;	#mm/tstep
	accudis=accuflux(riverldd,discharge)/upstreamarea;

	#	�������� ������
	#report	okadischarge.tss=timeoutput(observationpoint,accudis); #mm/tstep
	#report filt.tss=timeoutput(1,filtration);
	report okasoils.tss=timeoutput(1,soilstorage);
	#report perc.tss=timeoutput(1,percolation);
	#report basef.tss=timeoutput(1,baseflow);
	#report surf.tss=timeoutput(1,surfacewater);
	#report pot.tss=timeoutput(1,potevaporation);
	report okaevap.tss=timeoutput(1,pottotal);
	#report okaexcess.tss=timeoutput(1,excess);
	#report base.tss=timeoutput(1,basereservoir);
	report okaquick.tss=timeoutput(1,quickflow);
	report okabase.tss=timeoutput(1,baseflow);
	report okarun.tss=timeoutput(1,runoff);



