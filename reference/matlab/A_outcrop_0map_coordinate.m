%% 恢复单一露头的节理产状；
% 保留节理中倾向数据，输出节理端点坐标；
clc
clf
clear
close all
path1 = 'D:\作业\毕业论文\周咏霖'; 
path2 = pwd; 
path3 = 'D:\作业\毕业论文\周咏霖';
fileName='Outcrop';
%feval('setpath_outcrop')
%% 文件读取数据
cd(path1);      
mydata=xlsread('O76_process');                    % 加载数据； 
[~, outcropName, ~] = fileparts('O76');

ang0=mydata(1,8);                         % 露头测线走向；
n=mydata(1,9);                            % 露头节理数量；
M=mydata(:,1:7);                          % 露头节理位置、倾向、迹长；倾向数据；
%% %% 倾向转换为走向,节理端点坐标
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
XY
n = size(XY, 1);
X = [XY(:, [1, 3]), NaN(n, 1)]';  %仅抽取端点的第1、3列，即端点的x坐标，并且横向排列；
Y = [XY(:, [2, 4]), NaN(n, 1)]';   %仅抽取端点的第2、4列，即端点的y坐标，并且横向排列；
plot(X, Y, '-', 'Color',[0, 0, 0],'LineWidth',1);                  % 绘制裂缝底图
axis image
hold on

set(gca,'xtick',[],'xticklabel',[]);     %  不显示X、Y轴的刻度；
set(gca,'ytick',[],'yticklabel',[]);
set(gca,'linewidth',1,'fontsize',14,'fontname','Times New Roman')% 将图片边框及横纵设置：线宽2，字号14，字体Times New Roman
set(gca, 'LooseInset', [0,0,0,0])% % 裁掉图片的白边 (方便插图，省去手动裁剪的时间)
set(gcf,'unit','centimeters','position',[10 5 24 12])   


%% 输出
out=n;

excelfull= fullfile(path3, strcat(fileName,'.xlsx'));
writematrix(out, excelfull,'Sheet', outcropName,'Range', 'A1')

imagename=strcat(outcropName,'(',num2str(n),')','.png');    % 数据处理的图片命名;
imagenamesaveas=[path3,'\',imagename];         % 数据处理的图片保存;
set(gca,'FontSize',12,'Fontname', 'Times New Roman');% 图片的外边界为屏幕尺寸的大小,%ScreenSize is 四维向量[left, bottom, width, height]:
set(gcf, 'Color', 'w');
cd(path3);
exportgraphics(gcf,imagenamesaveas);
cd(path2)
close


