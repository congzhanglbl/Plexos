clear 
close all
clc
load('load.mat')
x=1:72; % Three days

figure(1)
plot(x,Load(:,1),'r')
hold on
xlabel('Time/h')
ylabel('Load/MW')
set(gca,'ylim',[100,1000],'yTick',[100:200:1000]); 
S_D_size3=[10 10 12 8];
S_D_size4=[.115 .12 .88 .85];    
set(gcf,'Units','centimeters','Position',S_D_size3);
set(gca,'Position',S_D_size4);
plot(x,Load(:,3),'r') % Copy from the Plexos model
plot(x,Load(:,6),'k') % Inflexible
plot(x,Load(:,7),'b') % Flexible
legend('Original Load data','Load Data from Plexos in BAU','Total Load Data in Inflexible case','Total Load Data in Flexible case')

figure(2)
plot(x,Load(:,5),'b')
hold on
xlabel('Time/h')
ylabel('Load/MW')
%set(gca,'ylim',[500,1000],'yTick',[500:100:1000]); 
S_D_size3=[10 10 12 8];
S_D_size4=[.115 .12 .88 .85];    
set(gcf,'Units','centimeters','Position',S_D_size3);
set(gca,'Position',S_D_size4);
plot(x,Load(:,4),'r')
legend('Original FCEV load','Load at Node 2 BAU case')

Load=Load_newFCEVdemand;
figure(3)
plot(x,Load(:,1),'r')
hold on
xlabel('Time/h')
ylabel('Load/MW')
set(gca,'ylim',[100,1000],'yTick',[100:200:1000]); 
S_D_size3=[10 10 12 8];
S_D_size4=[.115 .12 .88 .85];    
set(gcf,'Units','centimeters','Position',S_D_size3);
set(gca,'Position',S_D_size4);
plot(x,Load(:,3),'--r') % Copy from the Plexos model
plot(x,Load(:,6),'--k') % Inflexible
plot(x,Load(:,7),'--b') % Flexible
legend('Original Load data','Load Data from Plexos in BAU','Total Load Data in Inflexible case','Total Load Data in Flexible case')


load('load.mat')
Cost_Generation = [854.39;869.24;857.52];
Cost_Shutdown = [2400;2850;2400];
Cost_perMWh = [sum(Load(:,8))/sum(Load(:,1)),sum(Load(:,9))/sum(Load(:,6)),sum(Load(:,10))/sum(Load(:,1))];
fprintf('The total cost in 3 scenarios is: %.2f (BAU), %.2f (Inflexible), %.2f (Flexible) \n',sum(Load(:,8)),sum(Load(:,9)),sum(Load(:,10)))
fprintf('The total cost in 3 scenarios is: %.2f (BAU), %.2f (Inflexible), %.2f (Flexible) \n',sum(Load(:,8))/sum(Load(:,1)),sum(Load(:,9))/sum(Load(:,6)),sum(Load(:,10))/sum(Load(:,1)))

figure(122)
bar(Cost_perMWh,0.4);
ylabel('Cost per MWh($/MWh)')
%set(gca,'ylim',[15.5,16.5],'yTick',[15.5,0.2,16.5]); 
set(gca,'ylim',[15.8,16.1],'yTick',[15.8:0.1:16.1]); 
S_D_size3=[10 10 8 6];
S_D_size4=[.19 .10 .8 .85];
set(gcf,'Units','centimeters','Position',S_D_size3);
set(gca,'Position',S_D_size4);
name = {'BAU', 'Inflexible', 'Flexible'};
set(gca, 'XTickLabel', name);


figure(123)
bar(Cost_Generation,0.4);
ylabel('Costa(thousand $)')
set(gca,'ylim',[840,870],'yTick',[840:10:870]); 
S_D_size3=[12 10 8 6];
S_D_size4=[.16 .10 .83 .85];    
set(gcf,'Units','centimeters','Position',S_D_size3);
set(gca,'Position',S_D_size4);
name = {'BAU', 'Inflexible', 'Flexible'};
set(gca, 'XTickLabel', name);


figure(124)
bar(Cost_Shutdown,0.4);
ylabel('Cost($)')
set(gca,'ylim',[2100,3000],'yTick',[2100:200:3000]); 
S_D_size3=[14 10 8 6];
S_D_size4=[.18 .10 .80 .85];    
set(gcf,'Units','centimeters','Position',S_D_size3);
set(gca,'Position',S_D_size4);
name = {'BAU', 'Inflexible', 'Flexible'};
set(gca, 'XTickLabel', name);