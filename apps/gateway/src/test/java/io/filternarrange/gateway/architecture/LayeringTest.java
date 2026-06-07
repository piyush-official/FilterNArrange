// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.architecture;

import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

import static com.tngtech.archunit.library.Architectures.layeredArchitecture;

@AnalyzeClasses(packages = "io.filternarrange.gateway",
    importOptions = ImportOption.DoNotIncludeTests.class)
class LayeringTest {

    @ArchTest
    static final ArchRule LAYERS = layeredArchitecture().consideringAllDependencies()
        .layer("Api").definedBy("io.filternarrange.gateway.api..")
        .layer("Application").definedBy("io.filternarrange.gateway.application..")
        .layer("Domain").definedBy("io.filternarrange.gateway.domain..")
        .layer("Infrastructure").definedBy("io.filternarrange.gateway.infrastructure..")
        .layer("Platform").definedBy("io.filternarrange.gateway.platform..")

        .whereLayer("Api").mayNotBeAccessedByAnyLayer()
        .whereLayer("Application").mayOnlyBeAccessedByLayers("Api")
        .whereLayer("Infrastructure").mayOnlyBeAccessedByLayers("Platform", "Application", "Api")
        .whereLayer("Domain").mayOnlyBeAccessedByLayers("Application", "Infrastructure", "Api", "Platform");
}
