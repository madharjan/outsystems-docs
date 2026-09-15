#define BUILD_DIR "..\dist"
#define BUILD_FOLDER "OutSystems-Docs"
#define VERSION "1.0.1"

[Setup]
AppName=OutSystems-Docs MCP
AppVersion=1.0.1
AppPublisher=Community
AppCopyright=Copyright (c) 2026 OutSystems
LicenseFile=LICENSE.txt
PrivilegesRequired=lowest
DefaultDirName={autopf}\OutSystems-Docs
DefaultGroupName=OutSystems-Docs MCP
OutputDir={#BUILD_DIR}
OutputBaseFilename=OutSystems-Docs-Setup
Compression=lzma
SolidCompression=yes
ShowLanguageDialog=no
DisableWelcomePage=no
VersionInfoVersion=1.0.1.0

[Files]
Source: "{#BUILD_DIR}\{#BUILD_FOLDER}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\Configure Agents"; Filename: "{app}\osdocs-mcp.exe"; Parameters: "--agent-interactive"
Name: "{group}\Sync Documentation"; Filename: "{app}\osdocs-mcp.exe"; Parameters: "--sync"
Name: "{group}\Documentation"; Filename: "{app}\README.md"

[UninstallRun]
Filename: "{app}\osdocs-mcp.exe"; Parameters: "--agent-remove-all"; RunOnceId: "RemoveAgentConfigs"; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
{
  CRITICAL RULE: Keep agent list synchronized with src/osdocs/config.py
}
var
  AgentPage: TInputOptionWizardPage;
  OutputPage: TWizardPage;
  OutputMemo: TNewMemo;
  RestartPage: TOutputMsgWizardPage;
  SamplePage: TOutputMsgWizardPage;
  ReadmeButton: TNewButton;
  HFTokenPage: TInputQueryWizardPage;
  AgentNames: array[0..5] of String;
  InstallerLogFile: String;
  BackupCallCount: Integer;
  AppVersion: String;
  HFToken: String;

procedure LogToFile(const Message: String);
var
  Lines: TStringList;
  LogPath: String;
  LogDir: String;
  TimeStr: String;
begin
  try
    if InstallerLogFile = '' then
    begin
      InstallerLogFile := ExpandConstant('{app}\logs\osdocs-mcp-installer.log');
    end;
    LogPath := InstallerLogFile;
  except
    Exit;
  end;

  if LogPath <> '' then
  begin
    try
      LogDir := ExtractFileDir(LogPath);
      if LogDir <> '' then
      begin
        if not DirExists(LogDir) then
        begin
          ForceDirectories(LogDir);
        end;
      end;

      TimeStr := GetDateTimeString('', '-', ':');
      Lines := TStringList.Create;
      try
        if FileExists(LogPath) then
        begin
          Lines.LoadFromFile(LogPath);
        end;
        Lines.Add('[' + TimeStr + '] ' + Message);
        Lines.SaveToFile(LogPath);
      finally
        Lines.Free;
      end;
    except
      {Silent fail - logging system should not crash installation}
    end;
  end;
end;

procedure LogOutput(const Message: String);
begin
  if OutputMemo <> nil then
  begin
    OutputMemo.Lines.Add(Message);
  end;
  LogToFile('OUTPUT: ' + Message);
end;

procedure LogDebug(const Message: String);
begin
  LogToFile('DEBUG: ' + Message);
end;

procedure ListFilesRecursive(const RootPath: String; const RelativePath: String; var Count: Integer);
var
  FindRec: TFindRec;
  FilePath: String;
  FullPath: String;
begin
  FilePath := RootPath;
  if RelativePath <> '' then
    FilePath := FilePath + '\' + RelativePath;

  if FindFirst(FilePath + '\*', FindRec) then
  begin
    try
      repeat
        if (FindRec.Name <> '.') and (FindRec.Name <> '..') then
        begin
          FullPath := RelativePath;
          if FullPath <> '' then
            FullPath := FullPath + '\'
          else
            FullPath := '';
          FullPath := FullPath + FindRec.Name;

          if (FindRec.Attributes and $10) <> 0 then
          begin
            ListFilesRecursive(RootPath, FullPath, Count);
          end
          else
          begin
            Inc(Count);
            LogToFile('FILE: ' + FullPath);
          end;
        end;
      until not FindNext(FindRec);
    finally
      FindClose(FindRec);
    end;
  end;
end;

procedure LogBuildFilesList();
var
  BuildPath: String;
  FileCount: Integer;
begin
  try
    BuildPath := ExpandConstant('{#BUILD_DIR}\{#BUILD_FOLDER}');
    FileCount := 0;
    LogDebug('========== FILE MANIFEST ==========');
    LogDebug('Scanning build directory: ' + BuildPath);
    ListFilesRecursive(BuildPath, '', FileCount);
    LogDebug('Total files to be installed: ' + IntToStr(FileCount));
    LogDebug('========== END FILE MANIFEST ==========');
  except
    LogDebug('ERROR: Failed to enumerate files in build directory');
  end;
end;

procedure ReadmeButtonClick(Sender: TObject);
var
  ReadmePath: String;
  ResultCode: Integer;
begin
  try
    ReadmePath := ExpandConstant('{app}\README.md');
    if FileExists(ReadmePath) then
    begin
      ShellExec('open', ReadmePath, '', '', SW_SHOW, ewNoWait, ResultCode);
      LogDebug('Opened README.md: ' + ReadmePath);
    end
    else
    begin
      LogDebug('README.md not found at: ' + ReadmePath);
      ShellExec('open', ExpandConstant('{app}'), '', '', SW_SHOW, ewNoWait, ResultCode);
    end;
  except
    LogDebug('Failed to open README.md');
  end;
end;

function GetPageName(PageID: Integer): String;
var
  PageNum: Integer;
begin
  Result := '';
  PageNum := 0;
  case PageID of
    wpWelcome:            begin PageNum := 1; Result := 'Welcome'; end;
    wpLicense:            begin PageNum := 2; Result := 'License'; end;
    wpSelectDir:          begin PageNum := 3; Result := 'Select Directory'; end;
    wpSelectComponents:   begin PageNum := 4; Result := 'Select Components'; end;
    wpSelectProgramGroup: begin PageNum := 5; Result := 'Select Program Group'; end;
    wpSelectTasks:        begin PageNum := 6; Result := 'Select Tasks'; end;
    wpReady:              begin PageNum := 7; Result := 'Ready to Install'; end;
    wpPreparing:          begin PageNum := 8; Result := 'Preparing'; end;
    wpInstalling:         begin PageNum := 9; Result := 'Installing'; end;
    wpInfoAfter:          begin PageNum := 10; Result := 'Post-Install Info'; end;
    wpFinished:           begin PageNum := 11; Result := 'Finished'; end;
  end;
  if Result = '' then
  begin
    if (AgentPage <> nil) and (PageID = AgentPage.ID) then
    begin
      PageNum := 12;
      Result := 'Configure AI Agents';
    end
    else if (OutputPage <> nil) and (PageID = OutputPage.ID) then
    begin
      PageNum := 13;
      Result := 'Registering Agents';
    end
    else if (RestartPage <> nil) and (PageID = RestartPage.ID) then
    begin
      PageNum := 14;
      Result := 'Restart Required';
    end
    else if (HFTokenPage <> nil) and (PageID = HFTokenPage.ID) then
    begin
      PageNum := 15;
      Result := 'Hugging Face Token';
    end
    else if (SamplePage <> nil) and (PageID = SamplePage.ID) then
    begin
      PageNum := 16;
      Result := 'Finished Setup';
    end
    else
      Result := 'Unknown Page ' + IntToStr(PageID);
  end;
  if PageNum > 0 then
  begin
    if PageNum < 10 then
      Result := '0' + IntToStr(PageNum) + '. ' + Result
    else
      Result := IntToStr(PageNum) + '. ' + Result;
  end;
end;

procedure RunExe(const Params: String);
var
  ExePath: String;
  AppDir: String;
  ResultCode: Integer;
begin
  try
    AppDir := ExpandConstant('{app}');
    ExePath := AppDir + '\osdocs-mcp.exe';
    LogDebug('Executing: ' + ExePath + ' ' + Params);
    Exec(ExePath, Params, AppDir, SW_HIDE, ewWaitUntilTerminated, ResultCode);
    LogDebug('Command completed with exit code: ' + IntToStr(ResultCode));
    if ResultCode <> 0 then
      LogDebug('WARNING: Non-zero exit code returned');
  except
    LogDebug('ERROR: Failed to execute command');
  end;
end;

procedure SaveHFTokenToConfig(const Token: String);
var
  ConfigPath: String;
  Lines: TStringList;
  ConfigContent: String;
  Found: Boolean;
  i: Integer;
begin
  if Token = '' then
    Exit;

  try
    ConfigPath := ExpandConstant('{app}\config.yaml');
    Lines := TStringList.Create;
    try
      if FileExists(ConfigPath) then
        Lines.LoadFromFile(ConfigPath);

      Found := False;
      for i := 0 to Lines.Count - 1 do
      begin
        if Pos('hf_token:', LowerCase(Lines[i])) > 0 then
        begin
          Lines[i] := '  hf_token: "' + Token + '"';
          Found := True;
          Break;
        end;
      end;

      if not Found then
        Lines.Add('  hf_token: "' + Token + '"');

      Lines.SaveToFile(ConfigPath);
      LogDebug('HF_TOKEN saved to config.yaml');
    finally
      Lines.Free;
    end;
  except
    LogDebug('ERROR: Failed to save HF_TOKEN to config.yaml');
  end;
end;

procedure RunExeAndCapture(const Params: String);
var
  ExePath: String;
  BatchFile: String;
  OutputFile: String;
  ResultCode: Integer;
  Lines: TStringList;
  i: Integer;
begin
  try
    ExePath := ExpandConstant('{app}\osdocs-mcp.exe');
    BatchFile := ExpandConstant('{tmp}\run-agent-status.bat');
    OutputFile := ExpandConstant('{tmp}\osdocs-status-output.txt');

    LogDebug('Creating batch file: ' + BatchFile);
    LogDebug('Executing command: ' + ExePath + ' ' + Params);

    Lines := TStringList.Create;
    try
      Lines.Add('@echo off');
      Lines.Add('setlocal enabledelayedexpansion');
      Lines.Add('"' + ExePath + '" ' + Params);
      Lines.SaveToFile(BatchFile);
      LogDebug('Batch file created successfully');
    finally
      Lines.Free;
    end;

    LogDebug('Running batch file with output redirection');
    ShellExec('open', BatchFile, '> "' + OutputFile + '" 2>&1',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    LogDebug('Batch command returned exit code: ' + IntToStr(ResultCode));

    if FileExists(OutputFile) then
    begin
      LogDebug('Output file created successfully at: ' + OutputFile);
      Lines := TStringList.Create;
      try
        Lines.LoadFromFile(OutputFile);
        LogDebug('Read ' + IntToStr(Lines.Count) + ' lines from output');
        for i := 0 to Lines.Count - 1 do
        begin
          if Lines[i] <> '' then
            LogOutput(Lines[i]);
        end;
      finally
        Lines.Free;
        LogDebug('Cleaning up output file');
        DeleteFile(OutputFile);
      end;
    end
    else
    begin
      LogDebug('ERROR: Output file NOT created at: ' + OutputFile);
      LogDebug('Command may have failed to execute or produced no output');
    end;

    LogDebug('Cleaning up batch file');
    DeleteFile(BatchFile);
    LogDebug('RunExeAndCapture completed');
  except
    LogDebug('ERROR: Exception occurred in RunExeAndCapture');
  end;
end;

{ Documentation sync shells out to git.exe; install Git for Windows via winget
  (per-user, matching PrivilegesRequired=lowest) if it isn't already on PATH. }
procedure InstallGitIfMissing();
var
  ResultCode: Integer;
begin
  if Exec(ExpandConstant('{cmd}'), '/c where git', '', SW_HIDE,
    ewWaitUntilTerminated, ResultCode) and (ResultCode = 0) then
  begin
    LogDebug('Git for Windows already on PATH');
    Exit;
  end;

  LogDebug('Git not found on PATH, installing via winget...');
  LogOutput('Installing Git for Windows (required for documentation sync) ...');
  if Exec(ExpandConstant('{cmd}'),
    '/c winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements',
    '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0) then
  begin
    LogDebug('Git for Windows installed successfully via winget');
    LogOutput('... Done');
  end
  else
  begin
    LogDebug('WARNING: winget install of Git for Windows failed (exit code ' + IntToStr(ResultCode) + ')');
    LogOutput('... Could not auto-install Git. Install it manually from https://git-scm.com/download/win');
  end;
end;

procedure InitializeWizard;
var
  i: Integer;
begin
  AppVersion := ExpandConstant('{#VERSION}');
  LogDebug('========== WIZARD INITIALIZATION (v' + AppVersion + ') ==========');
  LogBuildFilesList();

  WizardForm.Caption := 'OutSystems-Docs MCP v' + AppVersion + ' Setup';

  { Initialize 6 primary platform agents }
  AgentNames[0] := 'Claude Code';
  AgentNames[1] := 'Claude Desktop';
  AgentNames[2] := 'Cursor IDE';
  AgentNames[3] := 'Gemini CLI';
  AgentNames[4] := 'GitHub Copilot (VS Code)';
  AgentNames[5] := 'OpenCode';

  LogDebug('Creating Agent configuration page with 6 primary platforms');
  AgentPage := CreateInputOptionPage(wpInstalling,
    'Configure AI Agents (v' + AppVersion + ')',
    'Select the AI Agents to register with OutSystems-Docs MCP.',
    'Your existing Agent configurations will be backed up before any changes are made. Additional agents are available via the configurator tool.',
    False, False);

  LogDebug('Adding primary platform agents to configuration page:');
  for i := 0 to 5 do
  begin
    AgentPage.Add(AgentNames[i]);
    LogDebug('  - ' + AgentNames[i]);
  end;

  LogDebug('Setting all agents to unchecked by default');
  for i := 0 to 5 do
  begin
    AgentPage.Values[i] := False;
  end;

  LogDebug('Creating Agent registration output page');
  OutputPage := CreateCustomPage(AgentPage.ID,
    'Registering Agents (v' + AppVersion + ')',
    'Setting up OutSystems-Docs MCP with your selected AI Agents ...');

  LogDebug('Configuring output memo control (terminal-style display)');
  OutputMemo := TNewMemo.Create(WizardForm);
  OutputMemo.Parent := OutputPage.Surface;
  OutputMemo.Left := ScaleX(0);
  OutputMemo.Top := ScaleY(0);
  OutputMemo.Width := OutputPage.Surface.Width;
  OutputMemo.Height := OutputPage.Surface.Height;
  OutputMemo.ScrollBars := ssBoth;
  OutputMemo.WordWrap := False;
  OutputMemo.ReadOnly := False;
  OutputMemo.Color := clBlack;
  OutputMemo.Font.Color := clGreen;
  OutputMemo.Font.Name := 'Courier New';
  OutputMemo.Font.Size := 8;

  LogDebug('Creating restart notification page');
  RestartPage := CreateOutputMsgPage(OutputPage.ID,
    'Restart Required (v' + AppVersion + ')',
    'OutSystems-Docs MCP has been registered with your selected AI Agents.',
    'To complete setup, please restart the AI Agent application(s) you selected.' + #13#10 + #13#10 +
    'After restarting, the OutSystems-Docs MCP server will appear in your Agent''s tool list.');

  LogDebug('Creating HF_TOKEN input page (2nd to last page)');
  HFTokenPage := CreateInputQueryPage(RestartPage.ID,
    'Hugging Face API Token (Optional)',
    'Configure Hugging Face Token',
    'Enter your Hugging Face API token (optional). Leave blank to skip:' + #13#10 + #13#10 +
    'How to get a token:' + #13#10 +
    '1. Go to https://huggingface.co/settings/tokens' + #13#10 +
    '2. Click "New token" and select "Read" access' + #13#10 +
    '3. Copy and paste the token below' + #13#10 + #13#10 +
    'Token helps download models faster. Not required to use the tool.');
  HFTokenPage.Add('HF_TOKEN:', False);

  LogDebug('Creating completion/samples page');
  SamplePage := CreateOutputMsgPage(HFTokenPage.ID,
    'You''re All Set! (v' + AppVersion + ')',
    'Sample prompts to get started with OutSystems-Docs MCP:',
    'AI Agent Prompt:' + #13#10 +
    '  "Explain the OutSystems platform architecture"' + #13#10 +
    '  "How do I create a responsive app in OutSystems?"' + #13#10 +
    '  "What are the best practices for OutSystems security?"' + #13#10 + #13#10 +
    'Documentation:' + #13#10 +
    '  Documentation synchronization will be triggered after installer completes.' + #13#10 +
    '  Run: osdocs-mcp.exe --sync' + #13#10 +
    '  To synchronize documentation with your local database.' + #13#10 + #13#10 +
    'Click "View Documentation" to open the README with detailed setup and usage information.');

  LogDebug('Creating documentation button on completion page');
  ReadmeButton := TNewButton.Create(WizardForm);
  ReadmeButton.Parent := SamplePage.Surface;
  ReadmeButton.Left := SamplePage.Surface.ClientWidth - ScaleX(180);
  ReadmeButton.Top := SamplePage.Surface.ClientHeight - ScaleY(40);
  ReadmeButton.Width := ScaleX(170);
  ReadmeButton.Height := ScaleY(25);
  ReadmeButton.Caption := 'View Documentation';
  ReadmeButton.OnClick := @ReadmeButtonClick;

  LogDebug('========== END WIZARD INITIALIZATION ==========');
end;

function BackButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  LogDebug('USER ACTION: Back button clicked on ' + GetPageName(CurPageID));
end;

procedure CurPageChanged(CurPageID: Integer);
var
  DefaultPath: String;
begin
  LogDebug('========== ' + GetPageName(CurPageID) + ' ==========');

  case CurPageID of
    wpWelcome:
      LogDebug('Welcome page: Starting OutSystems-Docs MCP installation');
    wpLicense:
      LogDebug('License page: User reviewing license agreement');
    wpSelectDir:
    begin
      try
        DefaultPath := ExpandConstant('{autopf}\OutSystems-Docs');
        LogDebug('Default install path: ' + DefaultPath);
        LogDebug('Current selected path: ' + WizardDirValue);
      except
        LogDebug('ERROR: Failed to get install path information');
      end;
    end;
    wpSelectComponents:
      LogDebug('Select Components page (may be hidden if no optional components)');
    wpSelectProgramGroup:
    begin
      LogDebug('Program group selection page - user can customize Start Menu folder name');
    end;
    wpSelectTasks:
      LogDebug('Select Tasks page (may be hidden if no optional tasks)');
    wpReady:
      LogDebug('Ready to Install page: User reviewing installation settings');
    wpPreparing:
      LogDebug('Preparing page: Installation in progress');
    wpInstalling:
      LogDebug('Installing page: Files being copied');
    wpInfoAfter:
      LogDebug('Post-Install Info page: Installation completed, awaiting user action');
    wpFinished:
      LogDebug('Finished page: Installation wizard closing');
  end;

  LogDebug('========== End of Stage ==========');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  LogDebug('========== SETUP STEP CHANGED ==========');

  case CurStep of
    ssInstall:
      LogDebug('Step: Installation beginning - files will be copied');
    ssPostInstall:
    begin
      InstallGitIfMissing();
      LogDebug('Step: Post-installation - running backup before Agent registration');
      Inc(BackupCallCount);
      LogDebug('Executing: --agent-backup (call #' + IntToStr(BackupCallCount) + ')');
      RunExe('--agent-backup');
      LogDebug('Agent configuration backup completed (call #' + IntToStr(BackupCallCount) + ')');
    end;
    ssDone:
    begin
      { osdocs-mcp.exe --sync is launched detached (ewNoWait), so it must never block on
        its own interactive overwrite-confirmation prompt (see sync.py) - the installer
        passes --yes to skip that prompt for this installer-triggered run. }
      LogDebug('Step: Installation complete - triggering documentation sync');
      LogDebug('Launching: osdocs-mcp.exe --sync --yes (external process)');
      if HFToken <> '' then
        Exec(ExpandConstant('{sys}\cmd.exe'), '/k "set HF_TOKEN=' + HFToken + ' && "' + ExpandConstant('{app}\osdocs-mcp.exe') + '" --sync --yes"', ExpandConstant('{app}'), SW_SHOW, ewNoWait, ResultCode)
      else
        Exec(ExpandConstant('{sys}\cmd.exe'), '/k "' + ExpandConstant('{app}\osdocs-mcp.exe') + '" --sync --yes', ExpandConstant('{app}'), SW_SHOW, ewNoWait, ResultCode);
      LogDebug('Sync process launched in background');
    end;
  end;

  LogDebug('========== END SETUP STEP ==========');
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  AgentKeys: array[0..5] of String;
  DefaultDir: String;
  SelectedDir: String;
  Selected: Boolean;
  i: Integer;
begin
  Result := True;
  LogDebug('USER ACTION: Next button clicked on ' + GetPageName(CurPageID));

  case CurPageID of
    wpSelectDir:
    begin
      try
        DefaultDir := ExpandConstant('{autopf}\OutSystems-Docs');
        SelectedDir := WizardDirValue;
        LogDebug('Install directory validation');
        LogDebug('  Default path: ' + DefaultDir);
        LogDebug('  Selected path: ' + SelectedDir);
        if SelectedDir = DefaultDir then
          LogDebug('  Path type: DEFAULT')
        else
          LogDebug('  Path type: USER CHANGED');
      except
        LogDebug('ERROR: Failed to validate install path');
      end;
    end;
    wpSelectProgramGroup:
    begin
      try
        LogDebug('Program Group: ' + WizardGroupValue);
      except
        LogDebug('ERROR: Failed to get program group value');
      end;
    end;
  end;

  if (HFTokenPage <> nil) and (CurPageID = HFTokenPage.ID) then
  begin
    LogDebug('========== CAPTURING HF_TOKEN ==========');
    HFToken := HFTokenPage.Values[0];
    if HFToken <> '' then
    begin
      LogDebug('HF_TOKEN captured (length: ' + IntToStr(Length(HFToken)) + ')');
      LogDebug('Saving HF_TOKEN to config.yaml');
      SaveHFTokenToConfig(HFToken);
      LogDebug('HF_TOKEN saved successfully');
    end
    else
      LogDebug('HF_TOKEN not provided (optional)');
    LogDebug('========== END HF_TOKEN CAPTURE ==========');
  end;

  if (AgentPage <> nil) and (CurPageID = AgentPage.ID) then
  begin
    LogDebug('========== AGENT REGISTRATION PROCESS ==========');

    { Primary platform agent keys (matching AgentNames) }
    AgentKeys[0] := 'claude_code';
    AgentKeys[1] := 'claude_desktop';
    AgentKeys[2] := 'cursor';
    AgentKeys[3] := 'gemini_cli';
    AgentKeys[4] := 'copilot_vscode';
    AgentKeys[5] := 'opencode';

    WizardForm.NextButton.Enabled := False;

    Selected := False;
    LogDebug('Scanning selected Agents:');
    for i := 0 to 5 do
    begin
      if AgentPage.Values[i] then
      begin
        LogDebug('  [SELECTED] ' + AgentNames[i] + ' (key: ' + AgentKeys[i] + ')');
        Selected := True;
      end
      else
      begin
        LogDebug('  [SKIPPED] ' + AgentNames[i]);
      end;
    end;

    if Selected then
    begin
      LogDebug('Executing Agent Registration ...');
      for i := 0 to 5 do
      begin
        if AgentPage.Values[i] then
        begin
          LogOutput('Registering: ' + AgentNames[i] + ' ...');
          LogDebug('Executing: --agent-add ' + AgentKeys[i]);
          RunExe('--agent-add ' + AgentKeys[i]);
          LogOutput('... Done');
        end;
      end;
    end;

    LogOutput('');
    LogOutput('Agent Configuration ...');
    LogDebug('Fetching Agent status...');
    RunExeAndCapture('--agent-status');
    LogOutput('... Done');

    WizardForm.NextButton.Enabled := True;
    LogDebug('========== END AGENT REGISTRATION ==========');
  end;
end;












