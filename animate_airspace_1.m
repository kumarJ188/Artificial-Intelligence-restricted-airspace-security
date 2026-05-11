% animate_airspace.m
% Playback of simulation_log.csv from Python test_run.py
%
% Keep the block below in sync with sim_state in test_run.py (run_tests).
% -------------------------------------------------------------------------
% --- sim_state (mirror test_run.py) --------------------------------------
GRID_X_MIN = 0;
GRID_X_MAX = 80;
GRID_Y_MIN = 0;
GRID_Y_MAX = 80;

% restricted_zone = [(30, 30), (40, 40)]  -> inclusive rectangle in Python
RZ_X1 = 30; RZ_Y1 = 30;
RZ_X2 = 40; RZ_Y2 = 40;

% no_fly_zones = [(20, 20), (22, 22)]  -> unit cells (1x1 at each)
NO_FLY = [20, 20; 22, 22];

% Initial positions (for on-plot caption; motion comes from CSV)
DEF0_X = 14; DEF0_Y = 14;
INT0_X = 64; INT0_Y = 64;
% -------------------------------------------------------------------------

close all;
clc;

logPath = 'simulation_log.csv';
if ~isfile(logPath)
    error('Missing %s — run Python test_run.py first (same folder as this .m file).', logPath);
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

rxLo = min(RZ_X1, RZ_X2);
rxHi = max(RZ_X1, RZ_X2);
ryLo = min(RZ_Y1, RZ_Y2);
ryHi = max(RZ_Y1, RZ_Y2);
rzW = rxHi - rxLo;
rzH = ryHi - ryLo;

% -------------------------------------------------------------------------
% FIX FOR APPLE SILICON RETINA (M1–M5):
%   getframe() captures at physical Retina resolution (2x or 3x logical px).
%   This causes diagonal lines / skewed / distorted video frames.
%
%   Solution: size the figure in POINTS and export each frame with
%   print('-r72'), which always gives exactly 1 pixel per point,
%   completely ignoring screen DPI. No Retina distortion possible.
%
%   Figure at 700 pt  +  print -r72  ==>  exactly 700x700 px per frame.
% -------------------------------------------------------------------------
fig = figure('Name', 'Python AI Simulation Playback', ...
    'Color', 'w', ...
    'MenuBar', 'none', ...
    'ToolBar', 'none', ...
    'Resize', 'off', ...
    'Units', 'points', ...           % <-- POINTS not pixels
    'Position', [100, 100, 700, 700], ...
    'Renderer', 'painters');         % <-- painters = pure software, no GPU scaling

axis equal;
axis([GRID_X_MIN GRID_X_MAX GRID_Y_MIN GRID_Y_MAX]);
grid on;
hold on;
xlabel('X');
ylabel('Y');
title(sprintf('Airspace (%d:%d) — sim_state from test_run.py', GRID_X_MIN, GRID_X_MAX));

nfzStr = sprintf('(%d,%d)', NO_FLY(1,1), NO_FLY(1,2));
for r = 2:size(NO_FLY, 1)
    nfzStr = [nfzStr, sprintf(', (%d,%d)', NO_FLY(r,1), NO_FLY(r,2))]; %#ok<AGROW>
end
cfgStr = sprintf([ ...
    'sim_state (test_run.py):\n' ...
    '  defender_pos = (%d, %d)\n' ...
    '  intruder_pos = (%d, %d)\n' ...
    '  grid_bounds = (%d,%d,%d,%d)\n' ...
    '  restricted_zone = [(%d,%d),(%d,%d)]\n' ...
    '  no_fly_zones = %s' ], ...
    DEF0_X, DEF0_Y, INT0_X, INT0_Y, ...
    GRID_X_MIN, GRID_X_MAX, GRID_Y_MIN, GRID_Y_MAX, ...
    RZ_X1, RZ_Y1, RZ_X2, RZ_Y2, nfzStr);
text(GRID_X_MIN + 0.5, GRID_Y_MAX - 0.5, cfgStr, 'VerticalAlignment', 'top', ...
    'FontSize', 8, 'BackgroundColor', [0.97 0.97 1], 'EdgeColor', [0.5 0.5 0.5], ...
    'Interpreter', 'none', 'Clipping', 'on');

rectangle('Position', [rxLo, ryLo, rzW, rzH], ...
    'FaceColor', [1 0.85 0.85], 'EdgeColor', 'r', 'LineWidth', 2);
text(mean([rxLo, rxHi]), mean([ryLo, ryHi]), 'Restricted', ...
    'HorizontalAlignment', 'center', 'Color', 'r', 'FontWeight', 'bold', 'FontSize', 11);

for i = 1:size(NO_FLY, 1)
    rectangle('Position', [NO_FLY(i,1), NO_FLY(i,2), 1, 1], ...
        'FaceColor', [0.55 0.55 0.55], 'EdgeColor', [0.3 0.3 0.3], 'LineWidth', 1);
end
text(NO_FLY(1,1)+0.5, NO_FLY(1,2)+0.5, 'NFZ', 'HorizontalAlignment', 'center', ...
    'FontSize', 8, 'Color', 'w', 'Clipping', 'on');

defenderPlot = scatter(logData.defender_x(1), logData.defender_y(1), 200, 'b', ...
    'filled', 'MarkerEdgeColor', 'k');
intruderPlot = scatter(logData.intruder_x(1), logData.intruder_y(1), 200, 'r', ...
    'filled', 'MarkerEdgeColor', 'k');
legend([defenderPlot, intruderPlot], {'Defender (MAX)', 'Intruder (MIN)'}, ...
    'Location', 'northwest', 'AutoUpdate', 'off');

drawnow;

% Temp folder for PNG frames
tmpDir = fullfile(tempdir, 'airspace_frames');
if exist(tmpDir, 'dir'), rmdir(tmpDir, 's'); end
mkdir(tmpDir);

% Video writer
videoFileName = 'Airspace_Simulation_Video.mp4';
v = VideoWriter(videoFileName, 'MPEG-4');
v.FrameRate = 2;
v.Quality = 95;
open(v);

nFrames = 0;
nFrames = printFrame(v, fig, tmpDir, nFrames);

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
    nFrames = printFrame(v, fig, tmpDir, nFrames);
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

for k = 1:5
    nFrames = printFrame(v, fig, tmpDir, nFrames);
end

close(v);
rmdir(tmpDir, 's');
fprintf('Video saved: %s (%d frames)\n', videoFileName, nFrames);

% =========================================================================
% LOCAL FUNCTION — replaces getframe() entirely.
%
% print(fig, path, '-dpng', '-r72') renders the figure off-screen at
% exactly 72 dpi. Because the figure is sized in points (1 pt = 1/72 in),
% the output is exactly <width_pt> x <height_pt> pixels regardless of the
% display's Retina scale factor. imread() then loads the clean PNG back.
% =========================================================================
function nFrames = printFrame(v, fig, tmpDir, nFrames)
    pngPath = fullfile(tmpDir, sprintf('f%06d.png', nFrames));
    print(fig, pngPath, '-dpng', '-r72');
    img = imread(pngPath);
    % Ensure even dimensions for MPEG-4
    [h, w, ~] = size(img);
    h = h - mod(h, 2);
    w = w - mod(w, 2);
    img = img(1:h, 1:w, :);
    writeVideo(v, img);
    nFrames = nFrames + 1;
end
