clear 
close all

x=[1:120]'; % 10 days

[num,txt, raw] = xlsread('10Days.xlsx',1);

% Plot 
figure(1)
plot(x,num(:,1),'b')
hold on
plot(x,num(:,2),'r')
xlabel('Time/h')
ylabel('Load/MW')
legend('BAU','Block')
fprintf('For Load, the BAU = %.2f GWh, the Block =  %.2f GWh \n', sum(num(:,1))*2/1000,sum(num(:,2))*2/1000)
Total_load_BAU = sum(num(:,1))*2/1000;
Total_load_Block = sum(num(:,2))*2/1000;

clear num raw
[num,txt, raw] = xlsread('10Days.xlsx',2);
% Plot Cost
figure(2)
plot(x,num(:,1),'b')
hold on
plot(x,num(:,2),'r')
xlabel('Time/h')
ylabel('Cost/$')
legend('BAU','Block')
fprintf('For cost, the BAU = %.2f GWh, the Block =  %.2f GWh \n', sum(num(:,1))*2,sum(num(:,2))*2)
Total_Cost_BAU = sum(num(:,1))*2;
Total_Cost_Block = sum(num(:,2))*2;

fprintf('For cost per unit, the BAU = %.2f $/MWh, the Block =  %.2f $/MWh \n',Total_Cost_BAU/Total_load_BAU/1000,Total_Cost_Block/Total_load_Block/1000)