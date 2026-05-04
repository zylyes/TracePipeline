%% 恢复单一露头的节理产状；
% 保留节理中倾向数据，输出节理端点坐标；
clc
clf
clear
close all
path1 = 'D:\HUO\Process\Beishan\Code_1_1outcrop\data'; 
path2 = pwd; 
path3 = 'D:\HUO\Process\Beishan\Code_1_1outcrop\result';
fileName='Outcrop';
feval('setpath_outcrop')
%% 文件读取数据
cd(path1);      
mydata=xlsread('O76');                    % 加载数据；
[~, outcropName, ~] = fileparts('O76');
ang0=mydata(1,8);                         % 露头测线走向；
n=mydata(1,9);                            % 露头节理数量；
M=mydata(:,1:7);                          % 露头节理位置、倾向、迹长；倾向数据；
%% 倾向转换为走向
dd=mydata(:,3);
traceAngles=zeros(n,1);
for e=1:n                             %    倾向转换为标准走向数据
    if dd(e,1)>=270
        traceAngles(e,1)=dd(e,1)+90-360;
    elseif dd(e,1)>=180
        traceAngles(e,1)=dd(e,1)-90;
    elseif dd(e,1)>=90
        traceAngles(e,1)=dd(e,1)-90;
    else
        traceAngles(e,1)=dd(e,1)+90;
    end
end
M(:,3)= traceAngles(:,1);
%% 节理端点坐标
XY=zeros(n,4);
traceLengths=zeros(n,1);                   
traceAngles=zeros(n,1);
XYLA=zeros(n,6);
dd=mydata(:,3); 
    for e=1:n          %    倾向转换为标准走向数据
        if dd(e,1)>=270
            traceAngles(e,1)=dd(e,1)+90-360;
        elseif dd(e,1)>=180
            traceAngles(e,1)=dd(e,1)-90;
        elseif dd(e,1)>=90
            traceAngles(e,1)=dd(e,1)-90;
        else
            traceAngles(e,1)=dd(e,1)+90;
        end
    end
      M(:,3)= traceAngles(:,1);   
for m=1:n
    traceLengths(m,1)=M(m,5)+M(m,7);
    traceAngles(m,1)=M(m,3);
    % [l1,l2,w1,w2,d1,d2]=Joint(ang0,M(m,1),M(m,2),M(m,3),M(m,4),M(m,5),M(m,6),M(m,7));
    [X1,Y1,X2,Y2]=Coordinate(ang0,M(m,1),M(m,2),M(m,3),M(m,4),M(m,5),M(m,6),M(m,7));   % Joints本身就会绘制图片；
    XY(m,:)=[X1,Y1,X2,Y2];                                                         % 节理的端点坐标XYXY形式；
   hold off
end
%%
XYLA=[XY,traceLengths,traceAngles];       
% 坐标平移
min_XX=abs(min(round(min(min(XY(:,1)),min(XY(:,3))))))+1;                          % X坐标中的最小值，用于坐标平移；
min_YY=abs(min(round(min(min(XY(:,2)),min(XY(:,4))))))+1;                          % Y坐标中的最小值，用于坐标平移；
lines=[XY(:,1)+min_XX,XY(:,2)+min_YY,XY(:,3)+min_XX,XY(:,4)+min_YY] ;              % 节理的端点坐标平移，保证所有坐标均为正值；
%% 旋转节理端点坐标，
% 依据露头测线角度计算旋转角度，将测线旋转为正北方向，方便计算露头分形维数；
if  ang0 <=360                            
    rotate_angle=-(360-ang0)*pi/180;                                                                               
elseif ang0 <=270
    rotate_angle=(ang0-180)*pi/180;
elseif ang0 <=180
    rotate_angle=-(180-ang0)*pi/180 ;
else ang0<=90;
    rotate_angle=ang0;
end
% 节理坐标旋转
rot_lines=zeros(length(lines),4);                                           % 存储旋转后的坐标矩阵
for i=1:size(lines, 1)
    rot_lines(i,1:2)= rotateVector(lines(i,1:2),rotate_angle);              % 旋转后的起点坐标值               
    rot_lines(i,3:4)= rotateVector(lines(i,3:4),rotate_angle);              % 旋转后的终点坐标值
end
min_rotXX=abs(min(round(min(min(rot_lines(:,1)),min(rot_lines(:,3))))));    % X坐标中的最小值，用于坐标平移；
min_rotYY=abs(min(round(min(min(rot_lines(:,2)),min(rot_lines(:,4))))));    % Y坐标中的最小值，用于坐标平移；
rotate_lines=[rot_lines(:,1)+min_rotXX,rot_lines(:,2)+min_rotYY,rot_lines(:,3)+min_rotXX,rot_lines(:,4)+min_rotYY] ;  % 节理的端点坐标平移，保证所有坐标均为正值；


%%
n = size(rotate_lines, 1);
X = [rotate_lines(:, [1, 3]), NaN(n, 1)]';  %仅抽取端点的第1、3列，即端点的x坐标，并且横向排列；
Y = [rotate_lines(:, [2, 4]), NaN(n, 1)]';   %仅抽取端点的第2、4列，即端点的y坐标，并且横向排列；
plot(X, Y, '-', 'Color',[0, 0, 0],'LineWidth',1);                  % 绘制裂缝底图
axis image
hold on

set(gca,'xtick',[],'xticklabel',[]);     %  不显示X、Y轴的刻度；
set(gca,'ytick',[],'yticklabel',[]);
set(gca,'linewidth',1,'fontsize',14,'fontname','Times New Roman')% 将图片边框及横纵设置：线宽2，字号14，字体Times New Roman
set(gca, 'LooseInset', [0,0,0,0])% % 裁掉图片的白边 (方便插图，省去手动裁剪的时间)
set(gcf,'unit','centimeters','position',[10 5 24 12])    
title({['Trace length map','(number=', num2str(length(XY)),')']; ['Scaline','(strike=', num2str(ang0), ')']}) ; 
%% 输出

out=ang0;

excelfull= fullfile(path3, strcat(fileName,'.xlsx'));
writematrix(out, excelfull,'Sheet', outcropName,'Range', 'A1')

imagename=strcat(outcropName,'(',num2str(ang0),')','.bmp');    % 数据处理的图片命名;
imagenamesaveas=[path3,'\',imagename];         % 数据处理的图片保存;
set(gca,'FontSize',12,'Fontname', 'Times New Roman');% 图片的外边界为屏幕尺寸的大小,%ScreenSize is 四维向量[left, bottom, width, height]:
set(gcf, 'Color', 'w');
cd(path3);feval('setpath_export_fig');  % 以屏幕输出为基础，-r分辨率，-m放大的倍数，-q压缩倍数，-native原始分辨率，-transparent透明
export_fig(imagenamesaveas, '-bmp', '-r600');
cd(path2)
close
