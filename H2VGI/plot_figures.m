

Cost_Generation = [854.39;869.24;857.52];
Cost_Shutdown = [2400;2850;2400];

figure(123)
bar(Cost_Generation,0.4);
ylabel('Cost/k$')
set(gca,'ylim',[840,870],'yTick',[840:10:870]); 
S_D_size3=[10 10 8 6];
S_D_size4=[.15 .10 .84 .85];    
set(gcf,'Units','centimeters','Position',S_D_size3);
set(gca,'Position',S_D_size4);
name = {'BAU', 'Inflexible', 'Flexible'};
set(gca, 'XTickLabel', name);


figure(124)
bar(Cost_Shutdown,0.4);
ylabel('Cost/$')
set(gca,'ylim',[2100,3000],'yTick',[2100:200:3000]); 
S_D_size3=[10 10 8 6];
S_D_size4=[.18 .10 .80 .85];    
set(gcf,'Units','centimeters','Position',S_D_size3);
set(gca,'Position',S_D_size4);
name = {'BAU', 'Inflexible', 'Flexible'};
set(gca, 'XTickLabel', name);