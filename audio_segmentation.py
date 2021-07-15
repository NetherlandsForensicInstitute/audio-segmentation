from collections import defaultdict
from tempfile import NamedTemporaryFile

import inaSpeechSegmenter
import pydub
from hansken_extraction_plugin.api.author import Author
from hansken_extraction_plugin.api.extraction_plugin import ExtractionPlugin
from hansken_extraction_plugin.api.maturity_level import MaturityLevel
from hansken_extraction_plugin.api.plugin_info import PluginInfo
from hansken_extraction_plugin.runtime.extraction_plugin_runner import run_with_hanskenpy
from logbook import Logger

log = Logger(__name__)


class AudioSegmentation(ExtractionPlugin):

    def plugin_info(self):
        log.info('pluginInfo request')
        plugin_info = PluginInfo(
            self,
            name='AudioSegmentation',
            version='2021.3.16',
            description='Audio Segmentation for Hansken',
            author=Author('FBDA', 'fbda@nfi.nl', 'NFI'),
            maturity=MaturityLevel.PROOF_OF_CONCEPT,
            webpage_url='https://hansken.org',
            matcher='(file.extension=wav OR file.extension=mp3) NOT file.misc.audioClassification AND $data.type=raw'
        )
        log.debug(f'returning plugin info: {plugin_info}')
        return plugin_info

    def process(self, trace, context):
        """
        Classify audio fragments, and write subfragments as child traces.
        Also write child traces with all fragments per category concatenated.

        :param trace: expected to be an audio file
        :param context: context
        """
        log.info(f"processing trace {trace.get('name')}")
        with NamedTemporaryFile('wb') as temporary_inputfragment:
            # Try to read in the fragment that we are going to process and store it temporarily
            temporary_inputfragment.write(trace.open().read(context.data_size()))
            fragment = pydub.AudioSegment.from_file(temporary_inputfragment.name)
            labeled_fragments = inaSpeechSegmenter.Segmenter(detect_gender=False)(temporary_inputfragment.name)

            # Initialize the defaultdict where we'll concatenate all fragments per category
            categorized_fragments = defaultdict(pydub.AudioSegment.empty)

            # This loop writes out each individual fragment as a child trace
            for i, (label, start, end) in enumerate(labeled_fragments):
                with NamedTemporaryFile('wb') as temporary_fragment:
                    fragment[start * 1000: end * 1000].export(temporary_fragment.name, format='wav')
                    child_trace = trace.child_builder(name=f'Fragment #{i} ({label}) in {trace.get("name")}')
                    with open(temporary_fragment.name, 'rb') as temporary_fragment:
                        child_trace.update(data={'raw': temporary_fragment.read()})
                        child_trace.update('file.misc.audioClassification', label)
                        child_trace.build()
                    # And concatenate the fragment to the others in the category to write it later
                    categorized_fragments[label] += fragment[start * 1000: end * 1000]
                    # TODO add a small bit of silence between fragments for easier listening

            # This loop writes out all concatenated fragments per category as a child trace
            for category, fragment in categorized_fragments.items():
                with NamedTemporaryFile('wb') as temporary_fragment:
                    child_trace = trace.child_builder(name=f'All {category} fragments in {trace.get("name")}')
                    fragment.export(temporary_fragment.name, format='wav')
                    with open(temporary_fragment.name, 'rb') as temporary_fragment:
                        child_trace.update(data={'raw': temporary_fragment.read()})
                        child_trace.update('file.misc.audioClassification', category)
                        child_trace.build()


if __name__ == '__main__':
    run_with_hanskenpy(AudioSegmentation)
