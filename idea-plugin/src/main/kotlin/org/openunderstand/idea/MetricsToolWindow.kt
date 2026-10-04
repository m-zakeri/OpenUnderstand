package org.openunderstand.idea

import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.execution.process.ProcessOutput
import com.intellij.execution.util.ExecUtil
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

private fun exec(vararg command: String): ProcessOutput =
    ExecUtil.execAndGetOutput(GeneralCommandLine(*command))

private fun canAnalyse(python: String) =
    try { exec(python, "-c", "import openunderstand").exitCode == 0 } catch (e: Exception) { false }

/**
 * Copy a bundled resource into a private temp directory, or null when it was not
 * bundled.
 *
 * The directory matters: Python puts a script's own directory first on
 * `sys.path`, so a shared one such as `/tmp` lets any file lying about shadow a
 * real module. A leftover `/tmp/openunderstand.py` from an earlier run is
 * exactly what made the dumper fail with "'openunderstand' is not a package".
 */
private fun unpack(resource: String, name: String): File? {
    val stream = MetricsToolWindow::class.java.getResourceAsStream(resource) ?: return null
    val file = File(FileUtil.createTempDirectory("openunderstand", null, true), name)
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
    val raw = unpack("/openunderstand.whl", "wheel.zip") ?: return null
    // ponytail: pure-Python wheel, so the compatibility tags are fixed. A wheel
    // with native code would need its real tags carried over instead.
    val version = ZipFile(raw).use { zip ->
        zip.entries().asSequence()
            .mapNotNull { Regex("""^openunderstand-([^/]+)\.dist-info/""").find(it.name) }
            .firstOrNull()?.groupValues?.get(1)
    } ?: return null
    val named = File(raw.parentFile, "openunderstand-$version-py3-none-any.whl")
    raw.renameTo(named)
    return named
}

/** The version a wheel filename carries, or "pypi" when nothing is bundled. */
private fun wheelVersion(wheel: File?) = wheel?.name?.split("-")?.getOrNull(1) ?: "pypi"

/**
 * The interpreter to analyse with: a virtualenv this plugin owns, installed from
 * the bundled wheel on first use and never asked about again.
 *
 * A venv rather than `pip install --user` because a distro python is externally
 * managed (PEP 668) and refuses to install into itself. The plugin's own venv
 * rather than one found on the machine because the analyser then matches the
 * plugin instead of whatever happens to be on the path -- which is the whole
 * reason the wheel is bundled at build time. Its two dependencies still come
 * from PyPI, so this pins the version without making the install offline.
 *
 * The directory carries the version, so a plugin update installs beside the old
 * one rather than reusing a venv holding the analyser it shipped with.
 */
private fun interpreter(progress: (String) -> Unit): Pair<String?, String?> {
    val wheel = unpackWheel()
    val dir = File(PathManager.getSystemPath(), "openunderstand-venv-${wheelVersion(wheel)}")
    // ponytail: POSIX layout only; add Scripts/python.exe when someone runs this on Windows.
    val python = File(dir, "bin/python")
    if (python.canExecute() && canAnalyse(python.absolutePath)) return python.absolutePath to null

    progress("Installing openunderstand")
    if (!python.canExecute()) {
        val made = try { exec("python3", "-m", "venv", dir.absolutePath) } catch (e: Exception) {
            return null to "No `python3` on the path to build a virtualenv with:\n\n${e.message}"
        }
        if (made.exitCode != 0)
            return null to "Could not create a virtualenv with `python3`:\n\n${made.stderr.take(2000)}"
    }
    val installed = exec(python.absolutePath, "-m", "pip", "install", "--upgrade",
        wheel?.absolutePath ?: "openunderstand")
    if (installed.exitCode != 0)
        return null to "Could not install openunderstand:\n\n${installed.stderr.take(2000)}"

    upgradeToAccelerated(python.absolutePath, wheelVersion(wheel), progress)
    return python.absolutePath to null
}

/**
 * Swap the bundled pure-Python wheel for the compiled one, if PyPI has a match.
 *
 * The analyser ships an optional C++ parse accelerator that parses Java about
 * 7.8x faster. It cannot be bundled: `speedy-antlr-tool` emits raw CPython C
 * API code with no `Py_LIMITED_API`, so a wheel is specific to one Python minor
 * *and* one platform, and the jar cannot know either until it is running on the
 * user's machine. PyPI can: `pip install` resolves the tag itself.
 *
 * So the bundled wheel stays the pure-Python one -- guaranteed to install, no
 * network, correct version -- and this is a best-effort upgrade on top of it.
 * `--only-binary` because compiling here would need a JDK, cmake and a C++17
 * compiler, and silently spending five minutes on that at first use is worse
 * than staying on the Python parser. Pinned to the same version so an upgrade
 * can only ever change the parser, never the analyser.
 *
 * Every failure is non-fatal by design: no network, no matching wheel, a
 * python the matrix does not cover. The analyser already falls back to the
 * pure-Python ANTLR runtime and says so once in its log.
 */
private fun upgradeToAccelerated(python: String, version: String, progress: (String) -> Unit) {
    // "pypi" is wheelVersion()'s answer when no wheel was bundled, which means
    // the install above already came from PyPI and pip already picked the best
    // wheel for this interpreter. Nothing to upgrade.
    if (version == "pypi") return
    progress("Looking for a compiled parser for this platform")
    val r = try {
        exec(python, "-m", "pip", "install", "--upgrade", "--only-binary=:all:",
            "openunderstand==$version")
    } catch (e: Exception) {
        return
    }
    if (r.exitCode != 0) return
    val accelerated = try {
        exec(python, "-c",
            "from openunderstand.utils import antler_parser as a; print(a.is_available())")
    } catch (e: Exception) {
        return
    }
    if (accelerated.stdout.trim() == "True") progress("Using the C++ parser")
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

/**
 * `--symbols` and `--references` output: a header row, then tab-separated rows.
 * Tabs because kind names hold spaces. A cell that reads as a number is kept as
 * an Int, so Line navigates and numeric columns sort as numbers.
 */
private fun parseTsv(output: String): Pair<List<String>, List<Array<Any?>>>? {
    val lines = output.lineSequence().filter { it.isNotBlank() }.toList()
    val header = lines.firstOrNull()?.split("\t")?.takeIf { it.firstOrNull() == "Entity" } ?: return null
    val rows = lines.drop(1).map { line ->
        line.split("\t").map<String, Any?> { it.toIntOrNull() ?: it }.toTypedArray()
    }
    return header to rows
}

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

/**
 * The table's model, which has to answer two questions `DefaultTableModel` gets
 * wrong here.
 *
 * `getColumnClass` is `Object` for every column there, and `TableRowSorter`
 * falls back to comparing `toString()` for a class that is not `Comparable` --
 * so a `CountLine` of 10 sorts before 2 and every numeric column sorts as text.
 * The class is settled once per analysis rather than per repaint, and stays
 * `Object` for a column whose values are not all one type, where a `Comparable`
 * comparator would throw instead.
 *
 * `isCellEditable` is true there, so the double-click that navigates to the
 * declaration also opens the cell for editing.
 */
private class MetricsModel : DefaultTableModel() {
    var columnClasses: List<Class<*>> = emptyList()
    override fun getColumnClass(column: Int): Class<*> =
        columnClasses.getOrElse(column) { Any::class.java }
    override fun isCellEditable(row: Int, column: Int) = false
}

class MetricsToolWindow : ToolWindowFactory {

    override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
        val model = MetricsModel()
        // AUTO_RESIZE_OFF: ~70 metric columns squeezed into the viewport width
        // leaves each one a few pixels wide. Let the scroll pane scroll instead.
        val table = JBTable(model).apply {
            autoCreateRowSorter = true
            autoResizeMode = JBTable.AUTO_RESIZE_OFF
        }
        val run = JButton("Analyse Project")
        val symbols = JButton("Symbol Table")
        val references = JButton("References")
        val export = JButton("Export CSV...")

        table.addMouseListener(object : MouseAdapter() {
            override fun mouseClicked(e: MouseEvent) {
                if (e.clickCount < 2) return
                val row = table.convertRowIndexToModel(table.rowAtPoint(e.point)).takeIf { it >= 0 } ?: return
                val file = LocalFileSystem.getInstance().findFileByPath(model.getValueAt(row, 1) as String) ?: return
                val line = (model.getValueAt(row, 2) as Int) - 1
                OpenFileDescriptor(project, file, line.coerceAtLeast(0), 0).navigate(true)
            }
        })

        export.addActionListener {
            if (model.rowCount == 0) {
                Messages.showInfoMessage(project, "Nothing to export yet.", "OpenUnderstand")
                return@addActionListener
            }
            val descriptor = FileSaverDescriptor("Export Metrics", "Save the table as CSV", "csv")
            FileChooserFactory.getInstance().createSaveFileDialog(descriptor, project)
                // Path overload, not the deprecated VirtualFile one -- untilBuild
                // is open, so a deprecated call is a future verifier failure.
                .save(null as java.nio.file.Path?, "metrics.csv")
                ?.file?.writeText(csv(model))
        }

        val buttons = listOf(run, symbols, references)
        /** Run the script with `args` and hand its stdout to `show`, or report why not. */
        fun launch(title: String, args: List<String>, show: (String) -> String?) {
            val root = project.basePath
            if (root == null) {
                Messages.showErrorDialog(project, "No project directory.", "OpenUnderstand")
                return
            }
            buttons.forEach { it.isEnabled = false }
            script(project, title, listOf(root) + args) { out, failure ->
                buttons.forEach { it.isEnabled = true }
                val error = failure ?: show(out!!)
                if (error != null) Messages.showErrorDialog(project, error, "OpenUnderstand")
            }
        }

        run.addActionListener {
            launch("Analysing Java sources", emptyList()) { out ->
                val rows = parse(out)
                if (rows.isEmpty()) "No metrics produced." else { show(model, rows); null }
            }
        }
        // The symbol table and the references share one table, so selecting a
        // reference's entity and asking again walks the graph one hop at a time.
        val showTable = { out: String ->
            parseTsv(out)?.let { (columns, rows) -> fill(model, columns, rows); null }
                ?: "Unexpected output from the analyser."
        }
        symbols.addActionListener {
            launch("Building the symbol table", listOf("--symbols")) { showTable(it) }
        }
        references.addActionListener {
            val selected = table.selectedRow
            if (selected < 0) {
                Messages.showInfoMessage(project, "Select an entity in the table first.", "OpenUnderstand")
                return@addActionListener
            }
            val entity = model.getValueAt(table.convertRowIndexToModel(selected), 0) as String
            launch("Finding references to $entity", listOf("--references", entity)) { showTable(it) }
        }

        val panel = JPanel(BorderLayout()).apply {
            add(JPanel().apply { add(run); add(symbols); add(references); add(export) }, BorderLayout.NORTH)
            add(JBScrollPane(table), BorderLayout.CENTER)
        }
        toolWindow.contentManager.addContent(
            ContentFactory.getInstance().createContent(panel, "", false))
    }

    private fun show(model: MetricsModel, rows: List<Row>) {
        val names = rows.flatMap { it.metrics.keys }.distinct()
        val data = rows.map { row ->
            (listOf<Any?>(row.entity, row.file, row.line) +
                names.map { row.metrics[it]?.toIntOrNull() ?: row.metrics[it] }).toTypedArray()
        }
        fill(model, listOf("Entity", "File", "Line") + names, data)
    }

    /** Every view keeps Entity, File and Line first: navigation and References read them. */
    private fun fill(model: MetricsModel, columns: List<String>, data: List<Array<Any?>>) {
        // Before setDataVector: it fires an event whose listeners ask for them.
        model.columnClasses = columns.indices.map { column ->
            data.mapNotNull { it.getOrNull(column)?.javaClass }.distinct().singleOrNull() ?: Any::class.java
        }
        model.setDataVector(data.toTypedArray(), columns.toTypedArray())
    }

    /** Run `idea_metrics.py args` off the UI thread; `done` gets stdout or an error. */
    private fun script(project: Project, title: String, args: List<String>,
                       done: (String?, String?) -> Unit) {
        ProgressManager.getInstance().run(object : Task.Backgroundable(project, title, true) {
            override fun run(indicator: ProgressIndicator) {
                indicator.isIndeterminate = true
                var out: String? = null
                var error: String? = null
                try {
                    val (python, failure) = interpreter { indicator.text = it }
                    if (python == null) {
                        error = failure
                    } else {
                        indicator.text = title
                        val script = unpack("/idea_metrics.py", "idea_metrics.py")!!
                        val result = exec(python, "-W", "ignore", script.absolutePath, *args.toTypedArray())
                        if (result.exitCode == 0) out = result.stdout
                        else error = "The analyser failed (exit ${result.exitCode}).\n\n" + result.stderr.take(2000)
                    }
                } catch (e: Exception) {
                    error = e.message ?: e.toString()
                }
                val o = out
                val m = error
                ApplicationManager.getApplication().invokeLater { done(o, m) }
            }
        })
    }
}
