chromosome_sort_order = [
    "chr1", "chr2", "chr3", "chr4", "chr5", "chr6", "chr7", "chr8", "chr9", "chr10", "chr11", "chr12", "chr13",
    "chr14", "chr15", "chr16", "chr17", "chr18", "chr19", "chr20", "chr21", "chr22", "chrX", "chrY"
    ]

def somatic_snv_tiering(somatic_snvs_query):
    """
    Tiering for somatic SNVs
    """
    # empty lists
    somatic_snvs_tier_one = []
    somatic_snvs_tier_two = []

    for v in somatic_snvs_query:
        variant = v.variant.variant
        gnomad = v.gnomad_popmax_af
        vaf = float(v.af) * 100
        all_vep_annotations = v.vep_annotations.all()
        all_hgvsc = []
        all_hgvsp = []
        all_gene = []
        all_consequences = []
        for vep_annotation in all_vep_annotations:
            all_hgvsc.append(vep_annotation.hgvsc)
            all_hgvsp.append(vep_annotation.hgvsp)
            all_gene.append(vep_annotation.transcript.gene.gene)
            consequences = vep_annotation.consequence.all()
            for consequence in consequences:
                all_consequences.append(consequence)
        impacts = list(set(consequence.impact.impact for consequence in all_consequences))
        consequences = [c.consequence for c in all_consequences]
        consequences_formatted = [c.replace("_", " ") for c in consequences]
        consequences_formatted = " | ".join(list(set(consequences)))
        hgvsc_formatted = " | ".join(all_hgvsc)
        hgvsp_formatted = " | ".join(all_hgvsp)
        force_display = v.force_display()
        status = v.get_status_display()
        id = v.id
        var_type = "somatic"
        checks = v.get_all_checks()

        # handle gnomad
        if float(gnomad) == -1:
            gnomad_formatted = "Not in Gnomad"
        else:
            gnomad_formatted = f"{gnomad:.3f}%"

        # make variant dict
        variant_dict = {
                "pk": variant,
                "gnomad": gnomad_formatted,
                "vaf": f"{vaf:.2f}",
                "hgvsc": hgvsc_formatted,
                "hgvsp": hgvsp_formatted,
                "gene": list(set(all_gene)),
                "consequence": consequences_formatted,
                "force_display": force_display,
                "status": status,
                "id": id,
                "var_type": var_type,
                "checks": checks

            }

        # lose >5% in gnomad and modifier only variants
        if float(gnomad) >= 0.05 or (len(impacts) == 1 and impacts[0] == "MODIFIER"):
            if not force_display:
                continue

        # Put in tier list
        if v.is_domain_zero:
            variant_dict["tier"] = "0"
            somatic_snvs_tier_one.append(variant_dict)
        elif v.is_domain_one:
            variant_dict["tier"] = "1"
            somatic_snvs_tier_one.append(variant_dict)
        elif v.is_domain_two:
            variant_dict["tier"] = "2"
            somatic_snvs_tier_two.append(variant_dict)
        else:
            pass

    return somatic_snvs_tier_one, somatic_snvs_tier_two


def germline_snv_tiering(germline_snvs_query):
    """
    Tiering for germline SNVs
    """

    germline_snvs_tier_one = []
    germline_snvs_tier_three = []

    for v in germline_snvs_query:
        variant = v.variant.variant
        gnomad = v.gnomad_popmax_af
        vaf = v.display_gt(v.gt)
        all_vep_annotations = v.vep_annotations.all()
        all_hgvsc = []
        all_hgvsp = []
        all_gene = []
        all_consequences = []
        for vep_annotation in all_vep_annotations:
            all_hgvsc.append(vep_annotation.hgvsc)
            all_hgvsp.append(vep_annotation.hgvsp)
            all_gene.append(vep_annotation.transcript.gene.gene)
            consequences = vep_annotation.consequence.all()
            for consequence in consequences:
                all_consequences.append(consequence)
        impacts = list(set(consequence.impact.impact for consequence in all_consequences))
        consequences = [c.consequence for c in all_consequences]
        consequences_formatted = [c.replace("_", " ") for c in consequences]
        consequences_formatted = " | ".join(list(set(consequences)))
        hgvsc_formatted = " | ".join(all_hgvsc)
        hgvsp_formatted = " | ".join(all_hgvsp)
        force_display = v.force_display()
        status = v.get_status_display()
        id = v.id
        var_type = "germline"
        checks = v.get_all_checks()

        # handle gnomad
        if float(gnomad) == -1:
            gnomad_formatted = "Not in Gnomad"
        else:
            gnomad_formatted = f"{gnomad:.3f}%"

        # make variant dict
        variant_dict = {
                "pk": variant,
                "gnomad": gnomad_formatted,
                "vaf": vaf,
                "hgvsc": hgvsc_formatted,
                "hgvsp": hgvsp_formatted,
                "gene": list(set(all_gene)),
                "consequence": consequences_formatted,
                "force_display": force_display,
                "status": status,
                "id": id,
                "var_type": var_type,
                "checks": checks
            }

        # lose >5% in gnomad and modifier only variants
        if float(gnomad) >= 0.05 or (len(impacts) == 1 and impacts[0] == "MODIFIER"):
            if not force_display:
                continue

        # Put in tier list
        if v.is_tier_zero:
            variant_dict["tier"] = "0"
            germline_snvs_tier_one.append(variant_dict)
        elif v.is_tier_one:
            variant_dict["tier"] = "1"
            germline_snvs_tier_one.append(variant_dict)
        elif v.is_tier_three:
            variant_dict["tier"] = "3"
            germline_snvs_tier_three.append(variant_dict)
        else:
            pass
    
    return germline_snvs_tier_one, germline_snvs_tier_three

def germline_cnv_tiering(germline_cnvs_query):
    """
    Tiering for germline CNVs
    """
    germline_cnvs_tier_one = []
    germline_cnvs_tier_three = []

    for v in germline_cnvs_query:
        variant = v.cnv.variant
        try:
            svlen = abs(v.cnv.svlen)
        except TypeError:
            svlen = v.cnv.svlen
        caller = v.cnv.caller
        gt = v.display_genotype()
        cn = v.cn
        try:
            maf = f"{(float(v.maf)*100):.1f}%"
        except TypeError:
            maf = "N/A"
        genes_tier_one = v.display_in_panel_genes("germline_cnv_tier_one")
        genes_tier_three = v.display_in_panel_genes("germline_cnv_tier_three")
        all_vep_annotations = v.vep_annotations.all()
        all_hgvsc = []
        all_hgvsp = []
        all_gene = []
        all_consequences = []
        all_cytoband = []
        for vep_annotation in all_vep_annotations:
            all_hgvsc.append(vep_annotation.hgvsc)
            all_hgvsp.append(vep_annotation.hgvsp)
            all_gene.append(vep_annotation.transcript.gene.gene)
            consequences = vep_annotation.consequence.all()
            for consequence in consequences:
                all_consequences.append(consequence)
            cytobands = vep_annotation.cytoband.all()
            for cytoband in cytobands:
                all_cytoband.append(cytoband)
        
        consequences = [c.consequence for c in all_consequences]
        consequences_formatted = [c.replace("_", " ") for c in consequences]
        consequences_formatted = " | ".join(list(set(consequences)))
        hgvsc_formatted = " | ".join(all_hgvsc)
        hgvsp_formatted = " | ".join(all_hgvsp)
        cytobands = [c.cytoband for c in all_cytoband]
        cytobands_formatted = " | ".join(list(set(cytobands)))
        status = v.get_status_display()
        id = v.id
        var_type = "germline"
        #checks = v.get_all_checks()

        # make variant dict
        variant_dict = {
                "pk": variant,
                "gt": gt,
                "cn": cn,
                "maf": maf,
                "hgvsc": hgvsc_formatted,
                "hgvsp": hgvsp_formatted,
                "genes_tier_one": genes_tier_one,
                "genes_tier_three": genes_tier_three,
                "consequence": consequences_formatted,
                "status": status,
                "id": id,
                "var_type": var_type,
                #"checks": checks,
                "cnv_or_sv": "cnv",
                "caller": caller,
                "svlen": svlen,
                "cytobands": cytobands_formatted        
            }

        # Put in tier list
        if v.is_tier_zero:
            variant_dict["tier"] = "0"
            germline_cnvs_tier_one.append(variant_dict)
        elif v.is_tier_one:
            variant_dict["tier"] = "1"
            germline_cnvs_tier_one.append(variant_dict)
        elif v.is_tier_three:
            variant_dict["tier"] = "3"
            germline_cnvs_tier_three.append(variant_dict)
        else:
            pass

    return germline_cnvs_tier_one, germline_cnvs_tier_three

def germline_sv_tiering(germline_svs_query):
    """
    Tiering for germline SVs, excluding BNDs
    """
    germline_svs_tier_one = []
    germline_svs_tier_three = []

    for v in germline_svs_query:
        variant = v.sv.variant
        try:
            svlen = abs(v.sv.svlen)
        except TypeError:
            svlen = v.sv.svlen
        caller = v.sv.caller
        pr = v.pr
        sr = v.sr
        vf = v.vf
        imprecise = v.imprecise
        somatic_score = v.somatic_score
        genes_tier_one = v.display_in_panel_genes("germline_cnv_tier_one")
        genes_tier_three = v.display_in_panel_genes("germline_cnv_tier_three")
        all_vep_annotations = v.vep_annotations.all()
        all_hgvsc = []
        all_hgvsp = []
        all_gene = []
        all_consequences = []
        all_cytoband = []
        for vep_annotation in all_vep_annotations:
            all_hgvsc.append(vep_annotation.hgvsc)
            all_hgvsp.append(vep_annotation.hgvsp)
            all_gene.append(vep_annotation.transcript.gene.gene)
            consequences = vep_annotation.consequence.all()
            for consequence in consequences:
                all_consequences.append(consequence)
            cytobands = vep_annotation.cytoband.all()
            for cytoband in cytobands:
                all_cytoband.append(cytoband)
        
        consequences = [c.consequence for c in all_consequences]
        consequences_formatted = [c.replace("_", " ") for c in consequences]
        consequences_formatted = " | ".join(list(set(consequences)))
        hgvsc_formatted = " | ".join(all_hgvsc)
        hgvsp_formatted = " | ".join(all_hgvsp)
        cytobands = [c.cytoband for c in all_cytoband]
        cytobands_formatted = " | ".join(list(set(cytobands)))
        status = v.get_status_display()
        id = v.id
        var_type = "germline"
        #checks = v.get_all_checks()

        # make variant dict
        variant_dict = {
                "pk": variant,
                "pr": pr,
                "sr": sr,
                "vf": vf,
                "imprecise": imprecise,
                "somatic_score": somatic_score,
                "hgvsc": hgvsc_formatted,
                "hgvsp": hgvsp_formatted,
                "genes_tier_one": genes_tier_one,
                "genes_tier_three": genes_tier_three,
                "consequence": consequences_formatted,
                "status": status,
                "id": id,
                "var_type": var_type,
                #"checks": checks,
                "cnv_or_sv": "sv",
                "caller": caller,
                "svlen": svlen,
                "cytobands": cytobands_formatted
            }

        # Put in tier list
        if v.is_tier_zero:
            variant_dict["tier"] = "0"
            germline_svs_tier_one.append(variant_dict)
        elif v.is_tier_one:
            variant_dict["tier"] = "1"
            germline_svs_tier_one.append(variant_dict)
        elif v.is_tier_three:
            variant_dict["tier"] = "3"
            germline_svs_tier_three.append(variant_dict)
        else:
            pass

    return germline_svs_tier_one, germline_svs_tier_three

def somatic_ploidy_display(somatic_ploidy_query):
    """
    Display the ploidy estimates for the somatic sample
    """
    ploidy_estimate_data = []

    for chrom in somatic_ploidy_query:
        ploidy_warning, ploidy_type = chrom.ploidy_warning()
        if ploidy_warning:
            domain_one_genes, domain_two_genes = chrom.tier_in_panel_genes()
            chrom_dict = {
                "chrom": chrom.chromosome,
                "ploidy_warning": ploidy_warning,
                "ploidy_type": ploidy_type,
                "chrom_message": chrom.whole_chromosome_message(),
                "distribution_message": chrom.cnv_distribution_message(),
                "proportion_message": chrom.cnv_proportion_message(),
                "domain_one_genes": domain_one_genes,
                "domain_two_genes": domain_two_genes
            }
            ploidy_estimate_data.append(chrom_dict)
    
    ploidy_estimates = []

    for chrom in chromosome_sort_order:
        for ploidy_estimate in ploidy_estimate_data:
            if chrom == ploidy_estimate["chrom"]:
                ploidy_estimates.append(ploidy_estimate)

    return ploidy_estimates

def somatic_cnv_tiering(somatic_cnvs_query):
    """
    Tiering for somatic CNVs
    """
    somatic_cnvs_domain_one = []
    somatic_cnvs_domain_two = []

    for v in somatic_cnvs_query:
        ploidy_objects = v.patient_analysis.ploidy.all()
        for ploidy_obj in ploidy_objects:
            if v in ploidy_obj.cnvs.all():
                continue

        variant = v.cnv.variant
        try:
            svlen = abs(v.cnv.svlen)
        except TypeError:
            svlen = v.cnv.svlen
        caller = v.cnv.caller
        gt = v.display_genotype()
        cn = v.cn
        try:
            maf = f"{(float(v.maf)*100):.1f}%"
        except TypeError:
            maf = "N/A"
        genes_domain_one = v.display_in_panel_genes("somatic_cnv_domain_one")
        genes_domain_two = v.display_in_panel_genes("somatic_cnv_domain_two")
        all_vep_annotations = v.vep_annotations.all()
        all_hgvsc = []
        all_hgvsp = []
        all_gene = []
        all_consequences = []
        all_cytoband = []
        for vep_annotation in all_vep_annotations:
            all_hgvsc.append(vep_annotation.hgvsc)
            all_hgvsp.append(vep_annotation.hgvsp)
            all_gene.append(vep_annotation.transcript.gene.gene)
            consequences = vep_annotation.consequence.all()
            for consequence in consequences:
                all_consequences.append(consequence)
            cytobands = vep_annotation.cytoband.all()
            for cytoband in cytobands:
                all_cytoband.append(cytoband)
        
        consequences = [c.consequence for c in all_consequences]
        consequences_formatted = [c.replace("_", " ") for c in consequences]
        consequences_formatted = " | ".join(list(set(consequences)))
        hgvsc_formatted = " | ".join(all_hgvsc)
        hgvsp_formatted = " | ".join(all_hgvsp)
        cytobands = [c.cytoband for c in all_cytoband]
        cytobands_formatted = " | ".join(sorted(list(set(cytobands))))
        status = v.get_status_display()
        id = v.id
        var_type = "somatic"
        #checks = v.get_all_checks()
        # make variant dict
        variant_dict = {
                "pk": variant,
                "gt": gt,
                "cn": cn,
                "maf": maf,
                "hgvsc": hgvsc_formatted,
                "hgvsp": hgvsp_formatted,
                "genes_domain_one": genes_domain_one,
                "genes_domain_two": genes_domain_two,
                "consequence": consequences_formatted,
                "status": status,
                "id": id,
                "var_type": var_type,
                #"checks": checks,
                "cnv_or_sv": "cnv",
                "caller": caller,
                "svlen": svlen,
                "cytobands": cytobands_formatted
            }

        # Put in tier list
        if v.is_domain_zero:
            variant_dict["tier"] = "0"
            somatic_cnvs_domain_one.append(variant_dict)
        elif v.is_domain_one:
            variant_dict["tier"] = "1"
            somatic_cnvs_domain_one.append(variant_dict)
        elif v.is_domain_two:
            variant_dict["tier"] = "2"
            somatic_cnvs_domain_two.append(variant_dict)
        else:
            pass

    return somatic_cnvs_domain_one, somatic_cnvs_domain_two


def somatic_sv_tiering(somatic_svs_query):
    """
    Tiering for germline SVs, excluding BNDs
    """
    somatic_svs_domain_one = []
    somatic_svs_domain_two = []

    for v in somatic_svs_query:
        variant = v.sv.variant
        try:
            svlen = abs(v.sv.svlen)
        except TypeError:
            svlen = v.sv.svlen
        caller = v.sv.caller
        pr = v.pr
        sr = v.sr
        vf = v.vf
        imprecise = v.imprecise
        somatic_score = v.somatic_score
        genes_domain_one = v.display_in_panel_genes("somatic_cnv_domain_one")
        genes_domain_two = v.display_in_panel_genes("somatic_cnv_domain_two")
        all_vep_annotations = v.vep_annotations.all()
        all_hgvsc = []
        all_hgvsp = []
        all_gene = []
        all_consequences = []
        all_cytoband = []
        for vep_annotation in all_vep_annotations:
            all_hgvsc.append(vep_annotation.hgvsc)
            all_hgvsp.append(vep_annotation.hgvsp)
            all_gene.append(vep_annotation.transcript.gene.gene)
            consequences = vep_annotation.consequence.all()
            for consequence in consequences:
                all_consequences.append(consequence)
            cytobands = vep_annotation.cytoband.all()
            for cytoband in cytobands:
                all_cytoband.append(cytoband)
        
        consequences = [c.consequence for c in all_consequences]
        consequences_formatted = [c.replace("_", " ") for c in consequences]
        consequences_formatted = " | ".join(list(set(consequences)))
        hgvsc_formatted = " | ".join(all_hgvsc)
        hgvsp_formatted = " | ".join(all_hgvsp)
        cytobands = [c.cytoband for c in all_cytoband]
        cytobands_formatted = " | ".join(list(set(cytobands)))
        status = v.get_status_display()
        id = v.id
        var_type = "somatic"
        #checks = v.get_all_checks()

        # make variant dict
        variant_dict = {
                "pk": variant,
                "pr": pr,
                "sr": sr,
                "vf": vf,
                "imprecise": imprecise,
                "somatic_score": somatic_score,
                "hgvsc": hgvsc_formatted,
                "hgvsp": hgvsp_formatted,
                "genes_domain_one": genes_domain_one,
                "genes_domain_two": genes_domain_two,
                "consequence": consequences_formatted,
                "status": status,
                "id": id,
                "var_type": var_type,
                #"checks": checks,
                "cnv_or_sv": "sv",
                "caller": caller,
                "svlen": svlen,
                "cytobands": cytobands_formatted
            }

        # Put in tier list
        if v.is_domain_zero:
            variant_dict["tier"] = "0"
            somatic_svs_domain_one.append(variant_dict)
        elif v.is_domain_one:
            variant_dict["tier"] = "1"
            somatic_svs_domain_one.append(variant_dict)
        elif v.is_domain_two:
            variant_dict["tier"] = "2"
            somatic_svs_domain_two.append(variant_dict)
        else:
            pass

    return somatic_svs_domain_one, somatic_svs_domain_two

def fusion_tiering(somatic_fusions_query):
    """
    Tiering for fusions - somatic only
    """

    fusions_domain_one = []
    fusions_domain_two = []

    for f in somatic_fusions_query:
        breakpoint1_genes_domain_one = f.breakpoint1.display_in_panel_genes("somatic_cnv_domain_one")
        breakpoint1_genes_domain_two = f.breakpoint1.display_in_panel_genes("somatic_cnv_domain_two")
        breakpoint1_genes = f.breakpoint1.sv.get_all_genes()
        breakpoint1_genes = list(set(breakpoint1_genes) - set(breakpoint1_genes_domain_one) - set(breakpoint1_genes_domain_two))
        breakpoint2_genes_domain_one = f.breakpoint2.display_in_panel_genes("somatic_cnv_domain_one")
        breakpoint2_genes_domain_two = f.breakpoint2.display_in_panel_genes("somatic_cnv_domain_two")
        breakpoint2_genes = f.breakpoint2.sv.get_all_genes()
        breakpoint2_genes = list(set(breakpoint2_genes) - set(breakpoint2_genes_domain_one) - set(breakpoint2_genes_domain_two))

        # make variant dict 
        variant_dict = {
            "pk": f.fusion_name,
            "fusion_type": f.fusion_type,
            "breakpoint1": f.breakpoint1.sv.chrom_pos,
            "breakpoint1_sv": f.breakpoint1.sv,
            "breakpoint1_pr": f.breakpoint1.pr,
            "breakpoint1_sr": f.breakpoint1.sr,
            "breakpoint1_vf": f.breakpoint1.vf,
            "breakpoint1_imprecise": f.breakpoint1.imprecise,
            "breakpoint1_somatic_score": f.breakpoint1.somatic_score,
            "breakpoint1_genes_domain_one": breakpoint1_genes_domain_one,
            "breakpoint1_genes_domain_two": breakpoint1_genes_domain_two,
            "breakpoint1_genes": breakpoint1_genes,
            "breakpoint2": f.breakpoint2.sv.chrom_pos,
            "breakpoint2_sv": f.breakpoint2.sv,
            "breakpoint2_pr": f.breakpoint2.pr,
            "breakpoint2_sr": f.breakpoint2.sr,
            "breakpoint2_vf": f.breakpoint2.vf,
            "breakpoint2_imprecise": f.breakpoint2.imprecise,
            "breakpoint2_somatic_score": f.breakpoint2.somatic_score,
            "breakpoint2_genes_domain_one": breakpoint2_genes_domain_one,
            "breakpoint2_genes_domain_two": breakpoint2_genes_domain_two,
            "breakpoint2_genes": breakpoint2_genes
        }

        # Put in tier list
        if f.is_domain_zero:
            variant_dict["tier"] = "0"
            fusions_domain_one.append(variant_dict)
        elif f.is_domain_one:
            variant_dict["tier"] = "1"
            fusions_domain_one.append(variant_dict)
        elif f.is_domain_two:
            variant_dict["tier"] = "2"
            fusions_domain_two.append(variant_dict)
    
    return fusions_domain_one, fusions_domain_two


def display_coverage(coverage_query, indication_obj):
    """
    Get the information for displaying coverage
    """
    gene_coverage = []
    #TODO handle threshold data better so it's flexible
    germline_threshold = 20
    somatic_threshold = 70
    _, all_genes = indication_obj.get_all_genes_and_panels()
    for coverage in coverage_query:
        coverage_dict = {
            "gene": coverage.gene.gene,
            "germline_average_depth": coverage.germline_average_depth,
            "germline_gene_coverage": coverage.germline_gene_coverage,
            "somatic_average_depth": coverage.somatic_average_depth,
            "somatic_gene_coverage": coverage.somatic_gene_coverage
        }
        if coverage_dict["gene"] in all_genes:
            gene_coverage.append(coverage_dict)
    return gene_coverage, germline_threshold, somatic_threshold


def display_mdt_notes(mdt_query):
    """
    Gets the information for the MDT notes page
    - previous mdt notes
    - variants table with classified variants
    """
    mdt_notes = []
    for mdt in mdt_query:
        mdt_dict = {
            "mdt_date": mdt.mdt_date,
            "user": mdt.user.username,
            "date": mdt.date,
            "notes": mdt.notes
        }
        mdt_notes.append(mdt_dict)
    return mdt_notes
