function [a1,b1,a2,b2]=Coordinate(ang0,r1,r2,ang,r3,r4,r5,r6)
%% 输入侧线走向、窗口位置、节理倾向和迹长；[a1,a2,b1,b2,e1,f1,e2,f2,g2,h2,j2,k2]对应不同类型节理的终点；
% 原算法中coordinate函数就是duandian函数的一部分，而Coordinates函数与Joint函数中的左迹长、右迹长的两种情况相同；
% 对于相交迹长，Joint函数输出的坐标值符号依然采用z3~z7，由于Coordinates函数用于采集裂缝参数，此时不同类型的裂缝共存；
% Coordinates函数则采用y2~y7描述相交迹长的数据，达到每一种类型节理的端点的都有独立符号对应的坐标值；
if ang0<90 
   ang_0=90-ang0;
else
   ang_0=450-ang0; 
end
   rad_0=ang_0/180*pi;

if ang<270  
    ang1=360-(ang+90);
else
    ang1=720-(90+ang);
end
%% 根据测线与节理的相对位置，将节理的走向角度ang1转换为弧度rada,rade；
if (r4~=0)&(r6==0)
    if ang_0<=180
        if (ang_0<ang1)&&(ang1<(180+ang_0))
            rada=ang1/180*pi;
        else
            rada=(ang1+180)/180*pi;
        end
    else
        if ((ang_0-180)<ang1)&&(ang1<ang_0)
            rada=(ang1+180)/180*pi;
        else
            rada=ang1/180*pi;
        end
    end
elseif (r4==0)&(r6~=0) 
    if ang_0<=180
        if (ang_0<ang1)&&(ang1<(180+ang_0))
            rade=(ang1+180)/180*pi;
        else
            rade=ang1/180*pi;
        end
    else
        if ((ang_0-180)<ang1)&&(ang1<ang_0)
            rade=ang1/180*pi;
        else
            rade=(ang1+180)/180*pi;
        end
    end
else (r4~=0)&(r6~=0);
    if ang_0<=180
        if (ang_0<ang1)&&(ang1<(180+ang_0))
            rada=ang1/180*pi;
            rade=(ang1+180)/180*pi;
        else
            rada=(ang1+180)/180*pi;
            rade=ang1/180*pi;
        end
    else
        if ((ang_0-180)<ang1)&&(ang1<ang_0)
            rada=(ang1+180)/180*pi;
            rade=ang1/180*pi;
        else
            rada=ang1/180*pi;
            rade=(ang1+180)/180*pi;
        end
    end
end 
%% 测线起点就是坐标零点，确定节理的起点和终点；
%  对于全迹长测量方法，根据迹长与测线的位置关系，共有三种情况，左迹长、右迹长、相交迹长；
%  针对左右迹长，可将原先代码中的switch变换为if，将c判断，转换为数值判断，这样就可以将原先的二选一，转换为共存；
%  针对相交迹长，将其分为左右迹长共存的模式；左边算左边，右边算右边，两者相加；
   z2=0;z3=0;z4=0;z5=0;z6=0;z7=0;
   y2=0;y3=0;y4=0;y5=0;y6=0;y7=0;
   z1=r1*(cos(rad_0)+1i*sin(rad_0));
if (r4~=0)&&(r6==0)     %左迹长；
   z2=r2*(cos(pi/2+rad_0)+1i*sin(pi/2+rad_0));
   z3=r3*(cos(rada)+1i*sin(rada));
   z4=r4*(cos(rada)+1i*sin(rada));
   
   a1=real(z1+z2+z3);  
   b1=imag(z1+z2+z3);   
   a2=real(z1+z2+z3+z4);
   b2=imag(z1+z2+z3+z4);
elseif (r4==0)&&(r6~=0) %右迹长；
   z2=r2*(cos(rad_0-pi/2)+1i*sin(rad_0-pi/2));
   z3=r5*(cos(rade)+1i*sin(rade));
   z4=r6*(cos(rade)+1i*sin(rade));
   a1=real(z1+z2+z3); 
   b1=imag(z1+z2+z3);
   a2=real(z1+z2+z3+z4);
   b2=imag(z1+z2+z3+z4);
else (r4~=0)&&(r6~=0);  %相交迹长；
   y2=r2*(cos(pi/2+rad_0)+1i*sin(pi/2+rad_0));
   y3=r3*(cos(rada)+1i*sin(rada));
   y4=r4*(cos(rada)+1i*sin(rada));
   y5=r2*(cos(rad_0-pi/2)+1i*sin(rad_0-pi/2));
   y6=r5*(cos(rade)+1i*sin(rade));
   y7=r6*(cos(rade)+1i*sin(rade));
   
   g1=real(z1+y2+y3);
   h1=imag(z1+y2+y3);
   a1=real(z1+y2+y3+y4);
   b1=imag(z1+y2+y3+y4);
         
   j1=real(z1+y5+y6);
   k1=imag(z1+y5+y6);
   a2=real(z1+y5+y6+y7);
   b2=imag(z1+y5+y6+y7);
end


   
