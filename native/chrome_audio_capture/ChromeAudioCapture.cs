using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;

namespace ConferenceRecorder.Native
{
    internal static class Program
    {
        private const int MinimumBuild = 20348;

        private static int Main(string[] args)
        {
            if (args.Length == 1 && args[0] == "--self-test")
            {
                return RunSelfTest();
            }
            if (args.Length != 2)
            {
                Console.Error.WriteLine("Uso: chrome-audio-capture.exe <PID> <salida.wav>");
                return 2;
            }

            int processId;
            if (!Int32.TryParse(args[0], out processId) || processId <= 0)
            {
                Console.Error.WriteLine("El PID debe ser un número entero positivo.");
                return 2;
            }

            if (!IsProcessLoopbackSupported())
            {
                Console.Error.WriteLine("La captura de audio por proceso requiere Windows build " + MinimumBuild + " o posterior.");
                return 3;
            }

            try
            {
                string outputPath = Path.GetFullPath(args[1]);
                string directory = Path.GetDirectoryName(outputPath);
                if (!String.IsNullOrEmpty(directory))
                {
                    Directory.CreateDirectory(directory);
                }

                using (ProcessLoopbackCapture capture = new ProcessLoopbackCapture(processId, outputPath))
                {
                    capture.Start();
                    Console.WriteLine("READY");
                    Console.Out.Flush();
                    capture.RunUntilStopped();
                }
                return 0;
            }
            catch (Exception error)
            {
                Console.Error.WriteLine("La captura de audio de Chrome ha fallado: " + error.Message);
                return 3;
            }
        }

        private static int RunSelfTest()
        {
            if (!IsProcessLoopbackSupported())
            {
                Console.Error.WriteLine("Captura de audio por proceso: no compatible; se requiere Windows build " + MinimumBuild + " o posterior.");
                return 1;
            }
            ProcessLoopbackCapture probe = new ProcessLoopbackCapture(
                Process.GetCurrentProcess().Id,
                Path.Combine(Path.GetTempPath(), "conference-recorder-probe.wav"));
            try
            {
                if (!probe.IsAgileCompletionHandler())
                {
                    Console.Error.WriteLine("Controlador de finalización: no ágil");
                    return 1;
                }
            }
            finally
            {
                probe.Dispose();
            }
            Console.WriteLine("Captura de audio por proceso: compatible");
            Console.WriteLine("Controlador de finalización: ágil");
            Console.WriteLine("Formato: PCM 44100 Hz, estéreo, 16 bits");
            return 0;
        }

        private static bool IsProcessLoopbackSupported()
        {
            if (NativeMethods.GetWindowsBuild() < MinimumBuild)
            {
                return false;
            }
            IntPtr library = NativeMethods.LoadLibrary("Mmdevapi.dll");
            if (library == IntPtr.Zero)
            {
                return false;
            }
            try
            {
                return NativeMethods.GetProcAddress(library, "ActivateAudioInterfaceAsync") != IntPtr.Zero;
            }
            finally
            {
                NativeMethods.FreeLibrary(library);
            }
        }
    }

    [ComVisible(true)]
    [ClassInterface(ClassInterfaceType.None)]
    internal sealed class ProcessLoopbackCapture : IActivateAudioInterfaceCompletionHandler, IAgileObject, IDisposable
    {
        private const string ProcessLoopbackDevice = "VAD\\Process_Loopback";
        private const int AudioClientActivationTypeProcessLoopback = 1;
        private const int ProcessLoopbackModeIncludeTargetProcessTree = 0;
        private const ushort VtBlob = 65;
        private const int AudioClientShareModeShared = 0;
        private const uint StreamFlagsLoopback = 0x00020000;
        private const uint StreamFlagsEventCallback = 0x00040000;
        private const uint StreamFlagsAutoConvertPcm = 0x80000000;
        private const uint BufferFlagsSilent = 0x00000002;

        private readonly int processId;
        private readonly string outputPath;
        private readonly ManualResetEvent activationCompleted = new ManualResetEvent(false);
        private readonly AutoResetEvent sampleReady = new AutoResetEvent(false);
        private readonly ManualResetEvent stopRequested = new ManualResetEvent(false);
        private IActivateAudioInterfaceAsyncOperation activationOperation;
        private IAudioClient audioClient;
        private IAudioCaptureClient captureClient;
        private WaveWriter writer;
        private int activationResult = unchecked((int)0x8000FFFF);
        private bool started;
        private bool comInitialized;
        private bool disposed;

        internal ProcessLoopbackCapture(int processId, string outputPath)
        {
            this.processId = processId;
            this.outputPath = outputPath;
        }

        internal void Start()
        {
            string stage = "CoInitializeEx";
            IntPtr activationBlob = IntPtr.Zero;
            IntPtr propertyVariant = IntPtr.Zero;
            try
            {
                int comResult = NativeMethods.CoInitializeEx(IntPtr.Zero, 0x0);
                if (comResult < 0 && comResult != unchecked((int)0x80010106))
                {
                    Marshal.ThrowExceptionForHR(comResult);
                }
                comInitialized = comResult >= 0;

                stage = "prepare activation parameters";
                activationBlob = Marshal.AllocHGlobal(12);
                Marshal.WriteInt32(activationBlob, 0, AudioClientActivationTypeProcessLoopback);
                Marshal.WriteInt32(activationBlob, 4, processId);
                Marshal.WriteInt32(activationBlob, 8, ProcessLoopbackModeIncludeTargetProcessTree);

                int propertySize = IntPtr.Size == 8 ? 24 : 16;
                propertyVariant = Marshal.AllocHGlobal(propertySize);
                for (int offset = 0; offset < propertySize; offset += 4)
                {
                    Marshal.WriteInt32(propertyVariant, offset, 0);
                }
                Marshal.WriteInt16(propertyVariant, 0, unchecked((short)VtBlob));
                Marshal.WriteInt32(propertyVariant, 8, 12);
                Marshal.WriteIntPtr(propertyVariant, IntPtr.Size == 8 ? 16 : 12, activationBlob);

                stage = "verify agile completion handler";
                if (!IsAgileCompletionHandler())
                {
                    throw new InvalidCastException("The COM callback does not expose IAgileObject.");
                }

                Guid audioClientId = typeof(IAudioClient).GUID;
                stage = "ActivateAudioInterfaceAsync";
                int result = NativeMethods.ActivateAudioInterfaceAsync(
                    ProcessLoopbackDevice,
                    ref audioClientId,
                    propertyVariant,
                    this,
                    out activationOperation);
                Marshal.ThrowExceptionForHR(result);
                stage = "wait for activation callback";
                if (!activationCompleted.WaitOne(TimeSpan.FromSeconds(10)))
                {
                    throw new TimeoutException("Windows did not activate process loopback within 10 seconds.");
                }
                Marshal.ThrowExceptionForHR(activationResult);
                if (audioClient == null)
                {
                    throw new InvalidOperationException("Windows returned no audio client.");
                }

                WaveFormat format = WaveFormat.CreatePcm44100Stereo();
                stage = "IAudioClient.Initialize";
                result = audioClient.Initialize(
                    AudioClientShareModeShared,
                    StreamFlagsLoopback | StreamFlagsEventCallback | StreamFlagsAutoConvertPcm,
                    0,
                    0,
                    ref format,
                    IntPtr.Zero);
                Marshal.ThrowExceptionForHR(result);

                Guid captureClientId = typeof(IAudioCaptureClient).GUID;
                IntPtr capturePointer;
                stage = "IAudioClient.GetService";
                Marshal.ThrowExceptionForHR(audioClient.GetService(ref captureClientId, out capturePointer));
                try
                {
                    captureClient = (IAudioCaptureClient)Marshal.GetObjectForIUnknown(capturePointer);
                }
                finally
                {
                    if (capturePointer != IntPtr.Zero)
                    {
                        Marshal.Release(capturePointer);
                    }
                }

                stage = "IAudioClient.SetEventHandle";
                Marshal.ThrowExceptionForHR(audioClient.SetEventHandle(sampleReady.SafeWaitHandle.DangerousGetHandle()));
                stage = "create WAV";
                writer = new WaveWriter(outputPath, format);
                stage = "IAudioClient.Start";
                Marshal.ThrowExceptionForHR(audioClient.Start());
                started = true;
            }
            catch (Exception error)
            {
                throw new InvalidOperationException(stage + ": " + error.Message, error);
            }
            finally
            {
                if (propertyVariant != IntPtr.Zero)
                {
                    Marshal.FreeHGlobal(propertyVariant);
                }
                if (activationBlob != IntPtr.Zero)
                {
                    Marshal.FreeHGlobal(activationBlob);
                }
            }
        }

        internal void RunUntilStopped()
        {
            Thread inputThread = new Thread(delegate()
            {
                try
                {
                    while (true)
                    {
                        string line = Console.ReadLine();
                        if (line == null || String.Equals(line.Trim(), "q", StringComparison.OrdinalIgnoreCase))
                        {
                            break;
                        }
                    }
                }
                finally
                {
                    stopRequested.Set();
                }
            });
            inputThread.IsBackground = true;
            inputThread.Name = "stop-input";
            inputThread.Start();

            WaitHandle[] handles = new WaitHandle[] { sampleReady, stopRequested };
            while (true)
            {
                int signaled = WaitHandle.WaitAny(handles, 1000);
                if (signaled == 1)
                {
                    break;
                }
                if (signaled == 0)
                {
                    DrainAvailablePackets();
                }
                if (!IsTargetAlive())
                {
                    throw new InvalidOperationException("Chrome was closed during the recording.");
                }
            }
            DrainAvailablePackets();
        }

        public int ActivateCompleted(IActivateAudioInterfaceAsyncOperation operation)
        {
            IntPtr audioPointer = IntPtr.Zero;
            try
            {
                int result = operation.GetActivateResult(out activationResult, out audioPointer);
                if (result >= 0 && activationResult >= 0 && audioPointer != IntPtr.Zero)
                {
                    audioClient = (IAudioClient)Marshal.GetObjectForIUnknown(audioPointer);
                }
                else if (result < 0)
                {
                    activationResult = result;
                }
            }
            catch (Exception error)
            {
                activationResult = Marshal.GetHRForException(error);
            }
            finally
            {
                if (audioPointer != IntPtr.Zero)
                {
                    Marshal.Release(audioPointer);
                }
                activationCompleted.Set();
            }
            return 0;
        }

        internal bool IsAgileCompletionHandler()
        {
            Guid agileId = typeof(IAgileObject).GUID;
            IntPtr unknown = Marshal.GetIUnknownForObject(this);
            IntPtr agile = IntPtr.Zero;
            try
            {
                return Marshal.QueryInterface(unknown, ref agileId, out agile) >= 0;
            }
            finally
            {
                if (agile != IntPtr.Zero)
                {
                    Marshal.Release(agile);
                }
                Marshal.Release(unknown);
            }
        }

        private void DrainAvailablePackets()
        {
            if (captureClient == null || writer == null)
            {
                return;
            }

            uint frames;
            Marshal.ThrowExceptionForHR(captureClient.GetNextPacketSize(out frames));
            while (frames > 0)
            {
                IntPtr data;
                uint flags;
                ulong devicePosition;
                ulong qpcPosition;
                Marshal.ThrowExceptionForHR(captureClient.GetBuffer(
                    out data,
                    out frames,
                    out flags,
                    out devicePosition,
                    out qpcPosition));
                try
                {
                    int byteCount = checked((int)frames * WaveFormat.BlockAlign44100Stereo);
                    if ((flags & BufferFlagsSilent) != 0 || data == IntPtr.Zero)
                    {
                        writer.WriteSilence(byteCount);
                    }
                    else
                    {
                        writer.Write(data, byteCount);
                    }
                }
                finally
                {
                    Marshal.ThrowExceptionForHR(captureClient.ReleaseBuffer(frames));
                }
                Marshal.ThrowExceptionForHR(captureClient.GetNextPacketSize(out frames));
            }
        }

        private bool IsTargetAlive()
        {
            try
            {
                using (Process process = Process.GetProcessById(processId))
                {
                    return !process.HasExited;
                }
            }
            catch (ArgumentException)
            {
                return false;
            }
        }

        public void Dispose()
        {
            if (disposed)
            {
                return;
            }
            disposed = true;
            try
            {
                if (started && audioClient != null)
                {
                    audioClient.Stop();
                }
            }
            finally
            {
                if (writer != null)
                {
                    writer.Dispose();
                    writer = null;
                }
                ReleaseComObject(captureClient);
                captureClient = null;
                ReleaseComObject(audioClient);
                audioClient = null;
                ReleaseComObject(activationOperation);
                activationOperation = null;
                activationCompleted.Dispose();
                sampleReady.Dispose();
                stopRequested.Dispose();
                if (comInitialized)
                {
                    NativeMethods.CoUninitialize();
                }
            }
        }

        private static void ReleaseComObject(object value)
        {
            if (value != null && Marshal.IsComObject(value))
            {
                Marshal.FinalReleaseComObject(value);
            }
        }
    }

    internal sealed class WaveWriter : IDisposable
    {
        private readonly FileStream stream;
        private readonly BinaryWriter writer;
        private readonly byte[] silence = new byte[16384];
        private long dataSize;
        private bool disposed;

        internal WaveWriter(string path, WaveFormat format)
        {
            stream = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.Read);
            writer = new BinaryWriter(stream);
            writer.Write(new char[] { 'R', 'I', 'F', 'F' });
            writer.Write((uint)0);
            writer.Write(new char[] { 'W', 'A', 'V', 'E' });
            writer.Write(new char[] { 'f', 'm', 't', ' ' });
            writer.Write((uint)16);
            writer.Write(format.FormatTag);
            writer.Write(format.Channels);
            writer.Write(format.SamplesPerSecond);
            writer.Write(format.AverageBytesPerSecond);
            writer.Write(format.BlockAlign);
            writer.Write(format.BitsPerSample);
            writer.Write(new char[] { 'd', 'a', 't', 'a' });
            writer.Write((uint)0);
        }

        internal void Write(IntPtr source, int count)
        {
            byte[] buffer = new byte[Math.Min(count, 65536)];
            int offset = 0;
            while (offset < count)
            {
                int chunk = Math.Min(buffer.Length, count - offset);
                Marshal.Copy(IntPtr.Add(source, offset), buffer, 0, chunk);
                writer.Write(buffer, 0, chunk);
                offset += chunk;
                dataSize += chunk;
            }
        }

        internal void WriteSilence(int count)
        {
            int remaining = count;
            while (remaining > 0)
            {
                int chunk = Math.Min(silence.Length, remaining);
                writer.Write(silence, 0, chunk);
                remaining -= chunk;
                dataSize += chunk;
            }
        }

        public void Dispose()
        {
            if (disposed)
            {
                return;
            }
            disposed = true;
            writer.Flush();
            if (dataSize > UInt32.MaxValue)
            {
                throw new IOException("The WAV file exceeded the 4 GB RIFF limit.");
            }
            stream.Position = 4;
            writer.Write((uint)(36 + dataSize));
            stream.Position = 40;
            writer.Write((uint)dataSize);
            writer.Flush();
            writer.Dispose();
            stream.Dispose();
        }
    }

    [StructLayout(LayoutKind.Sequential, Pack = 2)]
    internal struct WaveFormat
    {
        internal const int BlockAlign44100Stereo = 4;
        public ushort FormatTag;
        public ushort Channels;
        public uint SamplesPerSecond;
        public uint AverageBytesPerSecond;
        public ushort BlockAlign;
        public ushort BitsPerSample;
        public ushort ExtraSize;

        internal static WaveFormat CreatePcm44100Stereo()
        {
            WaveFormat format = new WaveFormat();
            format.FormatTag = 1;
            format.Channels = 2;
            format.SamplesPerSecond = 44100;
            format.BitsPerSample = 16;
            format.BlockAlign = BlockAlign44100Stereo;
            format.AverageBytesPerSecond = format.SamplesPerSecond * format.BlockAlign;
            format.ExtraSize = 0;
            return format;
        }
    }

    [ComVisible(true)]
    [Guid("41D949AB-9862-444A-80F6-C261334DA5EB")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    internal interface IActivateAudioInterfaceCompletionHandler
    {
        [PreserveSig]
        int ActivateCompleted(IActivateAudioInterfaceAsyncOperation operation);
    }

    [ComVisible(true)]
    [Guid("94EA2B94-E9CC-49E0-C0FF-EE64CA8F5B90")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IAgileObject
    {
    }

    [ComImport]
    [Guid("72A22D78-CDE4-431D-B8CC-843A71199B6D")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    internal interface IActivateAudioInterfaceAsyncOperation
    {
        [PreserveSig]
        int GetActivateResult(out int activateResult, out IntPtr activatedInterface);
    }

    [ComImport]
    [Guid("1CB9AD4C-DBFA-4C32-B178-C2F568A703B2")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    internal interface IAudioClient
    {
        [PreserveSig]
        int Initialize(int shareMode, uint streamFlags, long bufferDuration, long periodicity, ref WaveFormat format, IntPtr audioSessionGuid);
        [PreserveSig]
        int GetBufferSize(out uint bufferFrames);
        [PreserveSig]
        int GetStreamLatency(out long latency);
        [PreserveSig]
        int GetCurrentPadding(out uint paddingFrames);
        [PreserveSig]
        int IsFormatSupported(int shareMode, ref WaveFormat format, out IntPtr closestMatch);
        [PreserveSig]
        int GetMixFormat(out IntPtr deviceFormat);
        [PreserveSig]
        int GetDevicePeriod(out long defaultPeriod, out long minimumPeriod);
        [PreserveSig]
        int Start();
        [PreserveSig]
        int Stop();
        [PreserveSig]
        int Reset();
        [PreserveSig]
        int SetEventHandle(IntPtr eventHandle);
        [PreserveSig]
        int GetService(ref Guid interfaceId, out IntPtr service);
    }

    [ComImport]
    [Guid("C8ADBD64-E71E-48A0-A4DE-185C395CD317")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    internal interface IAudioCaptureClient
    {
        [PreserveSig]
        int GetBuffer(out IntPtr data, out uint frames, out uint flags, out ulong devicePosition, out ulong qpcPosition);
        [PreserveSig]
        int ReleaseBuffer(uint frames);
        [PreserveSig]
        int GetNextPacketSize(out uint frames);
    }

    internal static class NativeMethods
    {
        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        private struct RtlOsVersionInfo
        {
            internal uint Size;
            internal uint MajorVersion;
            internal uint MinorVersion;
            internal uint BuildNumber;
            internal uint PlatformId;
            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
            internal string ServicePack;
        }

        internal static int GetWindowsBuild()
        {
            RtlOsVersionInfo version = new RtlOsVersionInfo();
            version.Size = (uint)Marshal.SizeOf(typeof(RtlOsVersionInfo));
            int result = RtlGetVersion(ref version);
            return result == 0 ? checked((int)version.BuildNumber) : 0;
        }

        [DllImport("ntdll.dll", CharSet = CharSet.Unicode)]
        private static extern int RtlGetVersion(ref RtlOsVersionInfo versionInformation);

        [DllImport("Mmdevapi.dll", ExactSpelling = true, PreserveSig = true)]
        internal static extern int ActivateAudioInterfaceAsync(
            [MarshalAs(UnmanagedType.LPWStr)] string deviceInterfacePath,
            ref Guid interfaceId,
            IntPtr activationParams,
            IActivateAudioInterfaceCompletionHandler completionHandler,
            out IActivateAudioInterfaceAsyncOperation activationOperation);

        [DllImport("ole32.dll", ExactSpelling = true)]
        internal static extern int CoInitializeEx(IntPtr reserved, uint coInit);

        [DllImport("ole32.dll", ExactSpelling = true)]
        internal static extern void CoUninitialize();

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        internal static extern IntPtr LoadLibrary(string fileName);

        [DllImport("kernel32.dll", CharSet = CharSet.Ansi, SetLastError = true)]
        internal static extern IntPtr GetProcAddress(IntPtr module, string procedureName);

        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        internal static extern bool FreeLibrary(IntPtr module);
    }
}
