% animate_airspace.m
% Playback of simulation_log.csv from Python (test_run.py or run_scenario.py).
%
% If airspace_config.csv and no_fly_zones.csv exist (written by run_scenario.py),
% the script uses them. Otherwise the defaults match sim_state in test_run.py.
% -------------------------------------------------------------------------
cfgFile = 'airspace_config.csv';
if isfile(cfgFile)
    cfg = readtable(cfgFile);
    GRID_X_MIN = cfg.grid_x_min(1);
    GRID_X_MAX = cfg.grid_x_max(1);
    GRID_Y_MIN = cfg.grid_y_min(1);
    GRID_Y_MAX = cfg.grid_y_max(1);
    RZ_X1 = cfg.rz_x1(1); RZ_Y1 = cfg.rz_y1(1);
    RZ_X2 = cfg.rz_x2(1); RZ_Y2 = cfg.rz_y2(1);
    DEF0_X = cfg.def0_x(1); DEF0_Y = cfg.def0_y(1);
    INT0_X = cfg.int0_x(1); INT0_Y = cfg.int0_y(1);
    nfzFile = 'no_fly_zones.csv';
    if isfile(nfzFile)
        nfzTbl = readtable(nfzFile);
        v = nfzTbl.Properties.VariableNames;
        if height(nfzTbl) > 0 && all(ismember({'x1','y1','x2','y2'}, v))
            NO_FLY = [nfzTbl.x1, nfzTbl.y1, nfzTbl.x2, nfzTbl.y2];
        elseif height(nfzTbl) > 0 && all(ismember({'x','y'}, v))
            % Legacy: one cell per row -> 1x1 rectangle
            NO_FLY = [nfzTbl.x, nfzTbl.y, nfzTbl.x, nfzTbl.y];
        else
            NO_FLY = zeros(0, 4);
        end
    else
        NO_FLY = zeros(0, 4);
    end
else
    % Defaults (test_run sim_state): two 1x1 no-fly cells
    GRID_X_MIN = 0;
    GRID_X_MAX = 80;
    GRID_Y_MIN = 0;
    GRID_Y_MAX = 80;
    RZ_X1 = 30; RZ_Y1 = 30;
    RZ_X2 = 40; RZ_Y2 = 40;
    NO_FLY = [20, 20, 20, 20; 22, 22, 22, 22];
    DEF0_X = 14; DEF0_Y = 14;
    INT0_X = 64; INT0_Y = 64;
end
% -------------------------------------------------------------------------

close all;
clc;

logPath = 'simulation_log.csv';
if ~isfile(logPath)
    error('Missing %s — run Python test_run.py or run_scenario.py (same folder as this .m file).', logPath);
end

logData = readtable(logPath);

req = {'turn', 'defender_x', 'defender_y', 'intruder_x', 'intruder_y'};
for k = 1:numel(req)
    if ~ismember(req{k}, logData.Properties.VariableNames)
        error('CSV must contain column "%s". Found: %s', req{k}, strjoin(logData.Properties.VariableNames, ', '));
    end
end

n = height(logData);
if n < 1
    error('simulation_log.csv has no data rows (only header?). Run a full simulation.');
end

% Restricted zone rectangle (min/max handles corner order)
rxLo = min(RZ_X1, RZ_X2);
rxHi = max(RZ_X1, RZ_X2);
ryLo = min(RZ_Y1, RZ_Y2);
ryHi = max(RZ_Y1, RZ_Y2);
rzW = rxHi - rxLo;
rzH = ryHi - ryLo;

% Figure and axes — simple layout matching grid_bounds 0..80
% Fixed pixel size; VideoWriter (MPEG-4) needs every frame identical. HiDPI/retina
% and changing title text can otherwise make getframe sizes differ (e.g. 1050 vs 1048).
fig = figure('Name', 'Python AI Simulation Playback', 'Color', 'w', ...
    'Position', [100, 100, 700, 700], 'Units', 'pixels', 'Resize', 'off');
axis equal;
axis([GRID_X_MIN GRID_X_MAX GRID_Y_MIN GRID_Y_MAX]);
grid on;
hold on;
xlabel('X');
ylabel('Y');
title(sprintf('Airspace (%d:%d) — from simulation log', GRID_X_MIN, GRID_X_MAX));

if size(NO_FLY, 1) > 0
    nfzStr = sprintf('[(%d,%d),(%d,%d)]', NO_FLY(1,1), NO_FLY(1,2), NO_FLY(1,3), NO_FLY(1,4));
    for r = 2:size(NO_FLY, 1)
        nfzStr = [nfzStr, sprintf(', [(%d,%d),(%d,%d)]', NO_FLY(r,1), NO_FLY(r,2), NO_FLY(r,3), NO_FLY(r,4))]; %#ok<AGROW>
    end
else
    nfzStr = '(none)';
end
cfgStr = sprintf([ ...
    'Initial layout:\n' ...
    '  defender = (%d, %d)   intruder = (%d, %d)\n' ...
    '  view / grid: (%d,%d) to (%d,%d)\n' ...
    '  restricted = [(%d,%d),(%d,%d)]\n' ...
    '  no_fly = %s' ], ...
    DEF0_X, DEF0_Y, INT0_X, INT0_Y, ...
    GRID_X_MIN, GRID_Y_MIN, GRID_X_MAX, GRID_Y_MAX, ...
    RZ_X1, RZ_Y1, RZ_X2, RZ_Y2, nfzStr);
text(GRID_X_MIN + 0.5, GRID_Y_MAX - 0.5, cfgStr, 'VerticalAlignment', 'top', ...
    'FontSize', 8, 'BackgroundColor', [0.97 0.97 1], 'EdgeColor', [0.5 0.5 0.5], ...
    'Interpreter', 'none', 'Clipping', 'on');

rectangle('Position', [rxLo, ryLo, rzW, rzH], ...
    'FaceColor', [1 0.85 0.85], 'EdgeColor', 'r', 'LineWidth', 2);
text(mean([rxLo, rxHi]), mean([ryLo, ryHi]), 'Restricted', ...
    'HorizontalAlignment', 'center', 'Color', 'r', 'FontWeight', 'bold', 'FontSize', 11);

for i = 1:size(NO_FLY, 1)
    x1 = NO_FLY(i,1); y1 = NO_FLY(i,2); x2 = NO_FLY(i,3); y2 = NO_FLY(i,4);
    xlo = min(x1, x2); xhi = max(x1, x2);
    ylo = min(y1, y2); yhi = max(y1, y2);
    rw = xhi - xlo;
    rh = yhi - ylo;
    rectangle('Position', [xlo, ylo, rw, rh], ...
        'FaceColor', [0.55 0.55 0.55], 'EdgeColor', [0.3 0.3 0.3], 'LineWidth', 1);
end
if size(NO_FLY, 1) > 0
    x1 = NO_FLY(1,1); y1 = NO_FLY(1,2); x2 = NO_FLY(1,3); y2 = NO_FLY(1,4);
    xlo = min(x1, x2); xhi = max(x1, x2);
    ylo = min(y1, y2); yhi = max(y1, y2);
    text(mean([xlo, xhi]), mean([ylo, yhi]), 'NFZ', 'HorizontalAlignment', 'center', ...
        'FontSize', 8, 'Color', 'w', 'FontWeight', 'bold', 'Clipping', 'on');
end

defenderPlot = scatter(logData.defender_x(1), logData.defender_y(1), 200, 'b', ...
    'filled', 'MarkerEdgeColor', 'k');
intruderPlot = scatter(logData.intruder_x(1), logData.intruder_y(1), 200, 'r', ...
    'filled', 'MarkerEdgeColor', 'k');
legend([defenderPlot, intruderPlot], {'Defender (MAX)', 'Intruder (MIN)'}, ...
    'Location', 'northwest', 'AutoUpdate', 'off');

% --- Video (optional simple export) ---
% All frames are resized to VID x VID (even, stable for H.264/MPEG-4 in MATLAB)
VID = 700;
videoFileName = 'Airspace_Simulation_Video.mp4';
v = VideoWriter(videoFileName, 'MPEG-4');
v.FrameRate = 2;
v.Quality = 95;
open(v);

frame = getframeForVideo(fig, VID);
writeVideo(v, frame);

for t = 2:n
    title(sprintf('Turn %d (from simulation_log.csv)', logData.turn(t)));
    defenderPlot.XData = logData.defender_x(t);
    defenderPlot.YData = logData.defender_y(t);
    intruderPlot.XData = logData.intruder_x(t);
    intruderPlot.YData = logData.intruder_y(t);
    plot([logData.defender_x(t-1), logData.defender_x(t)], ...
         [logData.defender_y(t-1), logData.defender_y(t)], 'b-', 'LineWidth', 2);
    plot([logData.intruder_x(t-1), logData.intruder_x(t)], ...
         [logData.intruder_y(t-1), logData.intruder_y(t)], 'r--', 'LineWidth', 2);
    drawnow;
    writeVideo(v, getframeForVideo(fig, VID));
end

ix = logData.intruder_x(end);
iy = logData.intruder_y(end);
dx = logData.defender_x(end);
dy = logData.defender_y(end);
if dx == ix && dy == iy
    title(sprintf('Simulation Ended: DEFENDER WINS (%d steps)', n));
elseif ix >= rxLo && ix <= rxHi && iy >= ryLo && iy <= ryHi
    title('Simulation Ended: INTRUDER WINS (restricted zone)');
else
    title('Simulation Ended: No decisive outcome');
end

drawnow;
lastFrame = getframeForVideo(fig, VID);
for k = 1:5
    writeVideo(v, lastFrame);
end
close(v);
disp(['Video saved: ', videoFileName]);

% --- local function ---
function frame = getframeForVideo(figH, vidSize)
% vidSize: output height/width in pixels (same for every call — required by writeVideo)
    frame = getframe(figH);
    c = frame.cdata;
    if isempty(c)
        error('getframe returned empty; keep the figure window visible and retry.');
    end
    if size(c, 3) == 1
        c = repmat(c, [1 1 3]);
    end
    % Rescale to exact size (handles Retina / fractional scaling; avoids width/height drift
    % when the title or labels change the tight bounding box between frames)
    c = imresizeCdataToSquare(c, vidSize);
    [h, w, ~] = size(c);
    if mod(h, 2) == 1
        c = cat(1, c, c(end, :, :));
    end
    if mod(w, 2) == 1
        c = cat(2, c, c(:, end, :));
    end
    frame.cdata = c;
end

function c = imresizeCdataToSquare(c, n)
% n x n, uint8, 3 channels — uses Image Processing Toolbox if available, else quick nearest
    [h, w, ~] = size(c);
    if h == n && w == n
        return
    end
    if exist('imresize', 'file') == 2
        c = imresize(c, [n, n], 'bilinear');
        return
    end
    % Nearest-neighbor down/up-sample (no Image Processing Toolbox)
    iy = (min(max(1, round( linspace(1, h, n) )), h))';  % n x 1
    ix =  min(max(1, round( linspace(1, w, n) )), w);    % 1 x n
    c2 = uint8(zeros(n, n, 3, 'uint8'));
    for ch = 1:3
        c2(:, :, ch) = c(iy, ix, ch);
    end
    c = c2;
end
