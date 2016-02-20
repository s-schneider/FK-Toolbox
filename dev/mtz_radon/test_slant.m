clear all; close all; clc;
addpath('/home/contenti/raid5/contenti/mcodes/');

deg = 30:90;
dt = 0.2;


lead = 15;
ilead = round(lead ./ dt);

for n = 1:length(deg)
    
    P = taupTime('prem', 0, 'P', 'deg', deg(n));
    p(n) = P(1).rayParam / (180 / pi);  % give s / deg
    P = P(1).time;
    
    P200s = taupTime('prem', 0, 'P200s', 'deg', deg(n));
    P200s = P200s(1).time;
    
    P410s = taupTime('prem', 0, 'P400s', 'deg', deg(n));
    P410s = P410s(1).time;
    
    P670s = taupTime('prem', 0, 'P670s', 'deg', deg(n));
    P670s = P670s(1).time;
    
    dt200 = P200s - P;
    dt410 = P410s - P;
    dt670 = P670s - P;
    
%     dt200 = 23.24;
%     dt410 = 42.62;
%     dt670 = 69.3;
    
    i200 = round(dt200 ./ dt);
    i410 = round(dt410 ./ dt);
    i670 = round(dt670 ./ dt);
    
    d( (ilead + 1), n) = 1;
    d( (ilead+i200), n) = 0.25;    
    d( (ilead+i410), n) = 0.25;
    d( (ilead+i670), n) = 0.25;

end

% Add buffer to end
d = [d; zeros(ilead, size(d, 2))];

d1 = d;
[w,tw] = ricker(10,0.004);
d = conv2(d, w, 'same');

% Time axis
t = (0:size(d, 1)-1).*dt - lead;

% Add noise
% SNR = 0.75;
% n = rand(size(d));
% n = repmat(n, 3, 3);
% n = conv2(n, ones(10, 10), 'same');
% n = n ./ max(max(abs(n)));
% n = n((length(t)+1):2*length(t), (length(deg)+1):2*length(deg));
% 
% d = d + (n ./ SNR);

[S, tau, deg] = rfun_slant_stack(d, t, p, dt);

[SMAX,IMAX,SMIN,IMIN] = extrema2(S);
[yi, xi] = ind2sub(size(S), IMAX);

xs = tau(xi(1:4));
ys = deg(yi(1:4));

%% Reference times
P = taupTime('prem', 0, 'P', 'deg', 60);
% p(n) = P(1).rayParam / (180 / pi);  % give s / deg
P = P(1).time;

P200s = taupTime('prem', 0, 'P200s', 'deg', 60);
P200s = P200s(1).time;

P410s = taupTime('prem', 0, 'P400s', 'deg', 60);
P410s = P410s(1).time;

P670s = taupTime('prem', 0, 'P670s', 'deg', 60);
P670s = P670s(1).time;

dt200 = P200s - P;
dt410 = P410s - P;
dt670 = P670s - P;

%% Plots
close all;
figure();
pcolor(deg, tau, S'); shading flat
ylabel('Delay Time [s]');
xlabel('Moveout [deg]');
hold on;
hline(dt200)
hline(dt410)
hline(dt670)
axis ij;

% % plot(0, 0, 'w+', 'MarkerSize', 15)
% % plot(65.5, 2.5, 'w+', 'MarkerSize', 15)
% % plot(41.5, 1.2, 'w+', 'MarkerSize', 15)
% h = vline(25.89, 'k');
% h = vline(46.9, 'k');
% h = vline(77.28, 'k');
% 
% plot(xs, ys, '.k');
% 
% subplot(122);
% imagesc(p, t, d);
% xlabel('Ray Parameter [s/deg]');
% ylabel('Delay Time [s]');
