package org.openunderstand.idea

import com.intellij.execution.configurations.GeneralCommandLine
import com.intellij.execution.util.ExecUtil
import com.intellij.ide.util.PropertiesComponent
import com.intellij.openapi.application.ApplicationManager
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
import javax.swing.JButton
import javax.swing.JPanel
import javax.swing.table.DefaultTableModel

private const val PYTHON_KEY = "openunderstand.python"

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

class MetricsToolWindow : ToolWindowFactory {

    override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
        val model = DefaultTableModel()
        val table = JBTable(model).apply { autoCreateRowSorter = true }
        val run = JButton("Analyse Project")
        val python = JButton("Python…")

        table.addMouseListener(object : MouseAdapter() {
            override fun mouseClicked(e: MouseEvent) {
                if (e.clickCount < 2) return
                val row = table.convertRowIndexToModel(table.rowAtPoint(e.point)).takeIf { it >= 0 } ?: return
                val file = LocalFileSystem.getInstance().findFileByPath(model.getValueAt(row, 1) as String) ?: return
                val line = (model.getValueAt(row, 2) as Int) - 1
                OpenFileDescriptor(project, file, line.coerceAtLeast(0), 0).navigate(true)
            }
        })

        python.addActionListener {
            val current = PropertiesComponent.getInstance().getValue(PYTHON_KEY, "python3")
            Messages.showInputDialog(project, "Python interpreter with `openunderstand` installed:",
                "OpenUnderstand", null, current, null)
                ?.let { PropertiesComponent.getInstance().setValue(PYTHON_KEY, it) }
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
            add(JPanel().apply { add(run); add(python) }, BorderLayout.NORTH)
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
                    val script = FileUtil.createTempFile("idea_metrics", ".py", true)
                    javaClass.getResourceAsStream("/idea_metrics.py")!!.use { it.copyTo(script.outputStream()) }
                    val python = PropertiesComponent.getInstance().getValue(PYTHON_KEY, "python3")
                    val out = ExecUtil.execAndGetOutput(
                        GeneralCommandLine(python, "-W", "ignore", script.absolutePath, root))
                    rows = parse(out.stdout)
                    if (rows.isEmpty()) {
                        error = "No metrics produced (exit ${out.exitCode}).\n\n" +
                            "Check that `$python -c \"import openunderstand\"` works; " +
                            "install it with `pip install openunderstand`, then set the " +
                            "interpreter with the Python… button.\n\n" + out.stderr.take(2000)
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