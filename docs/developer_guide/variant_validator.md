# SVD developer guide - Variant validator

## Adding new polys and artefacts

When submitting new polys or artefacts to the lists in SVD, the submission will be sent to the Variant Validator API - https://rest.variantvalidator.org/

Given the initial validation of data inputted into the form, e.g. ref and alt only consisting of A, C, T and G, the frequency of warnings will be reduced.

If Variant Validator identifies any issues with the submitted variant, it will return a warning.
SVD then filters the warnings, discriminating between what is a genuine warning, and what is just guidance.
This validation and filtering is found in `utils.py` within the `validate_variant()` function.

Below are the following warning messages you might expect to see that SVD treats as genuine warnings:
* **Variant reference (C) does not agree with reference sequence (G).**
    * The variant decription, e.g. c.472C>T, specifies that the reference base is a C, whereas the base at position 472 of the reference sequence is actually a G. The user must correct the description and resubmit it.
    * This warning is the reason why this validation of new polys and artefacts has been implemented. 
* **Using a transcript reference sequence to specify a variant position that lies outside of the reference sequence is not HGVS-compliant. Instead re-submit NC_000006.12:g.32038297C>T**
    * The Mane Select transcript is used by default, unless there is a preferred transcript.
    * The HGVS nomenclature does not allow variant descriptions in which the sequence alteration lies outside of the reference sequence, either wholly or in part. In this example, the sequence alteration has been determined in the chromosomal context relative to the transcript and the user is directed to submit NC_000006.12:g.32038297C>T for validation instead.
* **Uncertain positions are not currently supported.**
    * A variant cannot be submitted with an undefined position.
    * This warning is not anticipated to show because of the form that forces a variant to be submitted in a particular format.
* **None of the specified transcripts fully overlap the described variation in the genomic sequence.**
    * Some genome sequence variants will lie outside of genes and will not project onto (align with) a gene transcript. Some variants might project only partially onto a transcript. In both instances, this warning will be generated.
* **Failed to find sequence NC00010.10 in our sequence store.**
    * There are a few reasons for this to occur. But it may be possible that the variant position was typed incorrectly and is therefore outside the span of the enterred chromosome.
* **Unexpected Error, contact Bioinformatics.**
    * An attempt has been made to anticipate all possible warnings from the validator, but this cannot be proven to be done completely. This warning message catches anything unexpected. For example, in testing it was shown that variants in pseudogenes can produce this error.
    * These errors should be investigated by submitting the variant to variant validator API manually and studying the json file produced.

Other messages one might anticipate include a HTTP request error if the API request times out, or that the variant already appears in the poly or artefact list. 

Lots of the warnings outputted by variant validator are only relevant when submitted in other formats like HGVS. Because the 'add new poly' and 'add new artefact' forms only submit the variant in one format, these warnings should not matter and so are not built into our filtering of warnings.
More examples of warnings can be found here: https://github.com/openvar/VV_databases/blob/master/markdown/instructions.md