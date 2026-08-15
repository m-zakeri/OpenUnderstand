package org.openunderstand.idea

import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.execution.process.ProcessOutput
import com.intellij.execution.util.ExecUtil
import com.intellij.ide.util.PropertiesComponent
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.application.PathManager
import com.intellij.openapi.fileChooser.FileChooserFactory
import com.intellij.openapi.fileChooser.FileSaverDescriptor
import com.intellij.openapi.fileEditor.OpenFileDescriptor
import com.intellij.openapi.progress.ProgressIndicator
import com.intellij.openapi.progress.ProgressManager
import com.intellij.openapi.progress.Task
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.Messages
import com.intellij.openapi.util.io.FileUtil
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowFactory
import com.intellij.ui.components.JBScrollPane
import com.intellij.ui.table.JBTable
import com.intellij.ui.content.ContentFactory
import java.awt.BorderLayout
import java.awt.event.MouseAdapter
import java.awt.event.MouseEvent
import java.io.File
import java.util.zip.ZipFile
import javax.swing.JButton
import javax.swing.JPanel
import javax.swing.table.DefaultTableModel
import javax.swing.table.TableModel

private const val PYTHON_KEY = "openunderstand.python"

private fun exec(vararg command: String): ProcessOutput =
    ExecUtil.execAndGetOutput(GeneralCommandLine(*command))

/**
 * Interpreter to run the dumper with: the one explicitly set, else an activated
 * virtualenv, else a `.venv` at or above the analysed project, else `python3`.
 * `openunderstand` is usually installed in a venv, and a bare `python3` that
 * cannot import it is the failure everyone hits first.
 */
private fun python(root: String): String {
    PropertiesComponent.getInstance().getValue(PYTHON_KEY)?.let { return it }
    val candidates = sequence {
        System.getenv("VIRTUAL_ENV")?.let { yield(File(it, "bin/python")) }
        var dir: File? = File(root).absoluteFile
        while (dir != null) {
            yield(File(dir, ".venv/bin/python"))
            dir = dir.parentFile
        }
    }
    // ponytail: POSIX layout only; add Scripts/python.exe when someone runs this on Windows.
    return candidates.firstOrNull { it.canExecute() }?.absolutePath ?: "python3"
}

private fun canAnalyse(python: String) =
    try { exec(python, "-c", "import openunderstand").exitCode == 0 } catch (e: Exception) { false }

/** Whether this build carries the wheel, which decides where pip gets the package. */
private val bundled: Boolean
    get() = MetricsToolWindow::class.java.getResource("/openunderstand.whl") != null

/** Copy a bundled resource to a temp file, or null when it was not bundled. */
private fun unpack(resource: String, suffix: String): File? {
    val stream = MetricsToolWindow::class.java.getResourceAsStream(resource) ?: return null
    val file = FileUtil.createTempFile("openunderstand", suffix, true)
    stream.use { it.copyTo(file.outputStream()) }
    return file
}

/**
 * The bundled wheel, written out under a filename pip will accept.
 *
 * pip parses the distribution and version out of the *filename* and rejects
 * anything that is not `name-version-python-abi-platform.whl`, so the resource
 * cannot simply be copied to a temp file: `openunderstand.whl` fails with
 * "Invalid wheel filename (wrong number of parts)". The version is recovered
 * from the wheel's own `*.dist-info/` entry, which is the one place it is
 * guaranteed to agree with the metadata pip checks it against.
 */
private fun unpackWheel(): File? {
    val raw = unpack("/openunderstand.whl", ".zip") ?: return null
    // ponytail: pure-Python wheel, so the compatibility tags are fixed. A wheel
    // with native code would need its real tags carried over instead.
    val version = ZipFile(raw).use { zip ->
        zip.entries().asSequence()
            .mapNotNull { Regex("""^openunderstand-([^/]+)\.dist-info/""").find(it.name) }
            .firstOrNull()?.groupValues?.get(1)
    } ?: return null
    val named = File(FileUtil.createTempDirectory("openunderstand", "wheel", true),
        "openunderstand-$version-py3-none-any.whl")
    raw.copyTo(named, overwrite = true)
    return named
}

/**
 * Install the analyser into a virtualenv this plugin owns, and return its
 * interpreter. A venv rather than `pip install --user` because a distro python
 * is externally managed (PEP 668) and refuses to install into itself.
 *
 * Prefers the wheel bundled at build time, so the analyser matches the plugin
 * instead of whatever version PyPI currently serves. Its two dependencies still
 * come from PyPI, so this pins the version without making the install offline.
 */
private fun bootstrap(base: String): Pair<String?, String?> {
    val dir = File(PathManager.getSystemPath(), "openunderstand-venv")
    val interpreter = File(dir, "bin/python")
    if (!interpreter.canExecute()) {
        val made = exec(base, "-m", "venv", dir.absolutePath)
        if (made.exitCode != 0) return null to "Could not create a virtualenv with `$base`:\n\n${made.stderr.take(2000)}"
    }
    val wheel = unpackWheel()
    val installed = exec(interpreter.absolutePath, "-m", "pip", "install", "--upgrade",
        wheel?.absolutePath ?: "openunderstand")
    if (installed.exitCode != 0) return null to "Could not install openunderstand:\n\n${installed.stderr.take(2000)}"
    return interpreter.absolutePath to null
}

/** One row of `scripts/idea_metrics.py` output: `path:line: longname  K=V K=V`. */
private data class Row(val file: String, val line: Int, val entity: String,
                       val metrics: Map<String, String>)

private val LINE = Regex("""^(.+):(\d+): (\S+)\s+(.*)$""")

private fun parse(output: String): List<Row> = output.lineSequence().mapNotNull { text ->
    val m = LINE.matchEntire(text.trim()) ?: return@mapNotNull null
    val metrics = m.groupValues[4].split(" ").mapNotNull {
        val (k, v) = it.split("=", limit = 2).takeIf { p -> p.size == 2 } ?: return@mapNotNull null
        k to v
    }.toMap()
    Row(m.groupValues[1], m.groupValues[2].toInt(), m.groupValues[3], metrics)
}.toList()

/** RFC 4180: quote a field only when it contains a delimiter, quote or newline. */
private fun cell(value: Any?): String {
    val text = value?.toString() ?: ""
    return if (text.any { it == ',' || it == '"' || it == '\n' || it == '\r' })
        "\"" + text.replace("\"", "\"\"") + "\"" else text
}

private fun csv(model: TableModel): String = buildString {
    (0 until model.columnCount).joinTo(this, ",") { cell(model.getColumnName(it)) }
    append("\n")
    for (row in 0 until model.rowCount) {
        (0 until model.columnCount).joinTo(this, ",") { cell(model.getValueAt(row, it)) }
        append("\n")
    }
}

class MetricsToolWindow : ToolWindowFactory {

    override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
        val model = DefaultTableModel()
        // AUTO_RESIZE_OFF: ~70 metric columns squeezed into the viewport width
        // leaves each one a few pixels wide. Let the scroll pane scroll instead.
        val table = JBTable(model).apply {
            autoCreateRowSorter = true
            autoResizeMode = JBTable.AUTO_RESIZE_OFF
        }
        val run = JButton("Analyse Project")
        val export = JButton("Export CSV...")
        val interpreter = JButton("Python...")

        table.addMouseListener(object : MouseAdapter() {
            override fun mouseClicked(e: MouseEvent) {
                if (e.clickCount < 2) return
                val row = table.convertRowIndexToModel(table.rowAtPoint(e.point)).takeIf { it >= 0 } ?: return
                val file = LocalFileSystem.getInstance().findFileByPath(model.getValueAt(row, 1) as String) ?: return
                val line = (model.getValueAt(row, 2) as Int) - 1
                OpenFileDescriptor(project, file, line.coerceAtLeast(0), 0).navigate(true)
            }
        })

        interpreter.addActionListener {
            Messages.showInputDialog(project, "Python interpreter to run the analyser with:",
                "OpenUnderstand", null, python(project.basePath ?: "."), null)
                ?.let { PropertiesComponent.getInstance().setValue(PYTHON_KEY, it) }
        }

        export.addActionListener {
            if (model.rowCount == 0) {
                Messages.showInfoMessage(project, "Nothing to export yet.", "OpenUnderstand")
                return@addActionListener
            }
            val descriptor = FileSaverDescriptor("Export Metrics", "Save the table as CSV", "csv")
            FileChooserFactory.getInstance().createSaveFileDialog(descriptor, project)
                .save(null as com.intellij.openapi.vfs.VirtualFile?, "metrics.csv")
                ?.file?.writeText(csv(model))
        }

        run.addActionListener {
            val root = project.basePath
            if (root == null) {
                Messages.showErrorDialog(project, "No project directory.", "OpenUnderstand")
                return@addActionListener
            }
            run.isEnabled = false
            analyse(project, root) { rows, error ->
                run.isEnabled = true
                if (error != null) {
                    Messages.showErrorDialog(project, error, "OpenUnderstand")
                } else {
                    show(model, rows)
                }
            }
        }

        val panel = JPanel(BorderLayout()).apply {
            add(JPanel().apply { add(run); add(export); add(interpreter) }, BorderLayout.NORTH)
            add(JBScrollPane(table), BorderLayout.CENTER)
        }
        toolWindow.contentManager.addContent(
            ContentFactory.getInstance().createContent(panel, "", false))
    }

    private fun show(model: DefaultTableModel, rows: List<Row>) {
        val names = rows.flatMap { it.metrics.keys }.distinct()
        model.setDataVector(
            rows.map { row ->
                (listOf(row.entity, row.file, row.line) +
                    names.map { row.metrics[it]?.toIntOrNull() ?: row.metrics[it] }).toTypedArray()
            }.toTypedArray(),
            (listOf("Entity", "File", "Line") + names).toTypedArray())
    }

    private fun analyse(project: Project, root: String, done: (List<Row>, String?) -> Unit) {
        ProgressManager.getInstance().run(object : Task.Backgroundable(project, "Analysing Java sources", true) {
            override fun run(indicator: ProgressIndicator) {
                indicator.isIndeterminate = true
                var rows = emptyList<Row>()
                var error: String? = null
                try {
                    var python = python(root)
                    if (!canAnalyse(python)) {
                        var install = false
                        ApplicationManager.getApplication().invokeAndWait {
                            install = Messages.showYesNoDialog(project,
                                "`$python` cannot import openunderstand.\n\n" +
                                    "Install it into a virtualenv for this IDE? " +
                                    (if (bundled) "The package ships with the plugin; its two dependencies come from PyPI."
                                    else "This downloads the package and its dependencies from PyPI."),
                                "OpenUnderstand", Messages.getQuestionIcon()) == Messages.YES
                        }
                        if (!install) {
                            ApplicationManager.getApplication().invokeLater {
                                done(rows, "No interpreter with openunderstand installed. " +
                                    "Set one with the Python... button.")
                            }
                            return
                        }
                        indicator.text = "Installing openunderstand"
                        val (installed, failure) = bootstrap(python)
                        if (installed == null) {
                            ApplicationManager.getApplication().invokeLater { done(rows, failure) }
                            return
                        }
                        PropertiesComponent.getInstance().setValue(PYTHON_KEY, installed)
                        python = installed
                    }
                    indicator.text = "Analysing $root"
                    val script = unpack("/idea_metrics.py", ".py")!!
                    val out = exec(python, "-W", "ignore", script.absolutePath, root)
                    rows = parse(out.stdout)
                    if (rows.isEmpty()) {
                        error = "No metrics produced (exit ${out.exitCode}).\n\n" + out.stderr.take(2000)
                    }
                } catch (e: Exception) {
                    error = e.message ?: e.toString()
                }
                val result = rows
                val message = error
                ApplicationManager.getApplication().invokeLater { done(result, message) }
            }
        })
    }
}