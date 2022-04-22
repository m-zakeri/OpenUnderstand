from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import openunderstand.analysis_passes.class_properties as class_properties

class CastAndCastBy(JavaParserLabeledListener):
    cast = []

    def enterExpression5(self, ctx:JavaParserLabeled.Expression5Context):
        name = ctx.typeType()
        print(name)